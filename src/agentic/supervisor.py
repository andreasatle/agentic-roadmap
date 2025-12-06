from __future__ import annotations
from dataclasses import dataclass

from agentic.schemas import WorkerInput, CriticInput
from agentic.tool_registry import ToolRegistry
from agentic.logging_config import get_logger
from agentic.agent_dispatcher import AgentDispatcher
from agentic.supervisor_types import SupervisorState as State, SupervisorContext
logger = get_logger("agentic.supervisor")


@dataclass
class Supervisor:
    dispatcher: AgentDispatcher
    tool_registry: ToolRegistry
    max_loops: int = 5

    def __call__(self) -> dict:
        """
        Explicit FSM over PLAN → WORK → TOOL/CRITIC → END.
        Each agent/tool invocation is a state transition.
        """
        context = SupervisorContext(trace=[])
        state = State.PLAN

        while state != State.END and context.loops_used <= self.max_loops:
            context.loops_used += 1
            if state is State.PLAN:
                state = self._handle_plan(context)
            elif state is State.WORK:
                state = self._handle_work(context)
            elif state is State.TOOL:
                state = self._handle_tool(context)
            elif state is State.CRITIC:
                state = self._handle_critic(context)
            else:
                raise RuntimeError(f"Unknown supervisor state: {state}")

        if state != State.END:
            raise RuntimeError("Supervisor exited without reaching END state.")

        context.trace.append(
            {
                "state": State.END,
                "result": context.final_result,
                "decision": context.decision,
                "loops_used": context.loops_used,
            }
        )
        return {
            "plan": context.plan,
            "result": context.final_result,
            "decision": context.decision,
            "loops_used": context.loops_used,
        }

    def _handle_plan(self, context: SupervisorContext) -> State:
        planner_response = self.dispatcher.plan()
        logger.debug(f"[supervisor] PLAN call_id={planner_response.call_id}")
        context.plan = planner_response.output.task
        context.worker_id = planner_response.output.worker_id
        context.worker_input = WorkerInput(task=context.plan)
        context.trace.append(
            {
                "state": State.PLAN,
                "agent_id": planner_response.agent_id,
                "call_id": planner_response.call_id,
                "tool_name": None,
                "input": None,
                "output": planner_response.output,
            }
        )
        return State.WORK

    def _handle_work(self, context: SupervisorContext) -> State:
        if context.worker_input is None:
            raise RuntimeError("WORK state reached without worker_input in context.")
        if context.worker_id is None:
            raise RuntimeError("WORK state reached without worker_id in context.")

        worker_response = self.dispatcher.work(context.worker_id, context.worker_input)
        worker_output = worker_response.output
        context.worker_output = worker_output
        context.trace.append(
            {
                "state": State.WORK,
                "agent_id": worker_response.agent_id,
                "call_id": worker_response.call_id,
                "tool_name": None,
                "input": context.worker_input,
                "output": worker_output,
            }
        )

        if worker_output.result is not None:
            context.worker_result = worker_output.result
            context.critic_input = CriticInput(
                plan=context.plan, worker_answer=worker_output.result
            )
            return State.CRITIC

        if worker_output.tool_request is not None:
            context.tool_request = worker_output.tool_request
            return State.TOOL

        raise RuntimeError("WorkerOutput violated 'exactly one branch' invariant.")

    def _handle_tool(self, context: SupervisorContext) -> State:
        request = context.tool_request
        prev_worker_input = context.worker_input
        if request is None or prev_worker_input is None:
            raise RuntimeError("TOOL state reached without tool_request and worker_input.")

        entry = self.tool_registry.get(request.tool_name)
        if entry is None:
            raise RuntimeError(f"Unknown tool: {request.tool_name}")
        _, func, arg_type = entry
        if not isinstance(request.args, arg_type):
            raise TypeError(f"Args for '{request.tool_name}' must be {arg_type.__name__}")

        logger.debug(f"[supervisor] TOOL call: {request.tool_name}")
        tool_result = func(request.args)
        context.trace.append(
            {
                "state": State.TOOL,
                "agent_id": None,
                "call_id": None,
                "tool_name": request.tool_name,
                "input": request.args,
                "output": tool_result,
            }
        )
        context.tool_result = tool_result
        context.worker_input = WorkerInput(
            task=prev_worker_input.task,
            previous_result=prev_worker_input.previous_result,
            feedback=prev_worker_input.feedback,
            tool_result=tool_result,
        )
        return State.WORK

    def _handle_critic(self, context: SupervisorContext) -> State:
        if context.critic_input is None:
            raise RuntimeError("CRITIC state reached without critic_input in context.")

        critic_response = self.dispatcher.critique(context.critic_input)
        decision = critic_response.output
        context.decision = decision
        context.trace.append(
            {
                "state": State.CRITIC,
                "agent_id": critic_response.agent_id,
                "call_id": critic_response.call_id,
                "tool_name": None,
                "input": context.critic_input,
                "output": critic_response.output,
            }
        )

        if decision.decision == "ACCEPT":
            context.final_result = context.worker_result
            context.final_output = context.worker_output
            logger.info(f"[supervisor] ACCEPT after {context.loops_used} transitions")
            return State.END

        if decision.decision == "REJECT":
            context.feedback = decision.feedback
            prev_worker_input = context.worker_input
            if prev_worker_input is None:
                raise RuntimeError("Missing worker_input on REJECT transition.")
            context.worker_input = WorkerInput(
                task=prev_worker_input.task,
                previous_result=prev_worker_input.previous_result,
                feedback=decision.feedback,
                tool_result=prev_worker_input.tool_result,
            )
            logger.info(f"[supervisor] REJECT after {context.loops_used} transitions")
            return State.WORK

        raise RuntimeError("Critic decision must be ACCEPT or REJECT.")
