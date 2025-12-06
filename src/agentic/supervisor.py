from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from agentic.schemas import WorkerInput, CriticInput
from agentic.tool_registry import ToolRegistry
from agentic.logging_config import get_logger
from agentic.agent_dispatcher import AgentDispatcher
from agentic.supervisor_types import ContextKey as Ctx, SupervisorState as State
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
        context: dict[Ctx, Any] = {Ctx.LOOPS_USED: 0, Ctx.TRACE: []}
        state = State.PLAN

        while state != State.END and context[Ctx.LOOPS_USED] < self.max_loops:
            context[Ctx.LOOPS_USED] += 1
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

        context[Ctx.TRACE].append(
            {
                "state": State.END,
                "result": context[Ctx.FINAL_RESULT],
                "decision": context[Ctx.DECISION],
                "loops_used": context[Ctx.LOOPS_USED],
            }
        )
        return {
            "plan": context[Ctx.PLAN],
            "result": context[Ctx.FINAL_RESULT],
            "decision": context[Ctx.DECISION],
            "loops_used": context[Ctx.LOOPS_USED],
        }

    def _handle_plan(self, context: dict[Ctx, Any]) -> State:
        planner_response = self.dispatcher.plan()
        logger.debug(f"[supervisor] PLAN call_id={planner_response.call_id}")
        context[Ctx.PLAN] = planner_response.output.task
        context[Ctx.WORKER_INPUT] = WorkerInput(task=context[Ctx.PLAN])
        context[Ctx.TRACE].append(
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

    def _handle_work(self, context: dict[Ctx, Any]) -> State:
        worker_input = context.get(Ctx.WORKER_INPUT)
        if worker_input is None:
            raise RuntimeError("WORK state reached without worker_input in context.")

        worker_response = self.dispatcher.work(worker_input)
        worker_output = worker_response.output
        context[Ctx.WORKER_OUTPUT] = worker_output
        context[Ctx.TRACE].append(
            {
                "state": State.WORK,
                "agent_id": worker_response.agent_id,
                "call_id": worker_response.call_id,
                "tool_name": None,
                "input": worker_input,
                "output": worker_output,
            }
        )

        if worker_output.result is not None:
            context[Ctx.WORKER_RESULT] = worker_output.result
            context[Ctx.CRITIC_INPUT] = CriticInput(
                plan=context[Ctx.PLAN], worker_answer=worker_output.result
            )
            return State.CRITIC

        if worker_output.tool_request is not None:
            context[Ctx.TOOL_REQUEST] = worker_output.tool_request
            return State.TOOL

        raise RuntimeError("WorkerOutput violated 'exactly one branch' invariant.")

    def _handle_tool(self, context: dict[Ctx, Any]) -> State:
        request = context.get(Ctx.TOOL_REQUEST)
        prev_worker_input = context.get(Ctx.WORKER_INPUT)
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
        context[Ctx.TRACE].append(
            {
                "state": State.TOOL,
                "agent_id": None,
                "call_id": None,
                "tool_name": request.tool_name,
                "input": request.args,
                "output": tool_result,
            }
        )
        context[Ctx.TOOL_RESULT] = tool_result
        context[Ctx.WORKER_INPUT] = WorkerInput(
            task=prev_worker_input.task,
            previous_result=prev_worker_input.previous_result,
            feedback=prev_worker_input.feedback,
            tool_result=tool_result,
        )
        return State.WORK

    def _handle_critic(self, context: dict[Ctx, Any]) -> State:
        critic_input = context.get(Ctx.CRITIC_INPUT)
        if critic_input is None:
            raise RuntimeError("CRITIC state reached without critic_input in context.")

        critic_response = self.dispatcher.critique(critic_input)
        decision = critic_response.output
        context[Ctx.DECISION] = decision
        context[Ctx.TRACE].append(
            {
                "state": State.CRITIC,
                "agent_id": critic_response.agent_id,
                "call_id": critic_response.call_id,
                "tool_name": None,
                "input": critic_input,
                "output": critic_response.output,
            }
        )

        if decision.decision == "ACCEPT":
            context[Ctx.FINAL_RESULT] = context[Ctx.WORKER_RESULT]
            context[Ctx.FINAL_OUTPUT] = context[Ctx.WORKER_OUTPUT]
            logger.info(f"[supervisor] ACCEPT after {context[Ctx.LOOPS_USED]} transitions")
            return State.END

        if decision.decision == "REJECT":
            context[Ctx.FEEDBACK] = decision.feedback
            prev_worker_input = context.get(Ctx.WORKER_INPUT)
            if prev_worker_input is None:
                raise RuntimeError("Missing worker_input on REJECT transition.")
            context[Ctx.WORKER_INPUT] = WorkerInput(
                task=prev_worker_input.task,
                previous_result=prev_worker_input.previous_result,
                feedback=decision.feedback,
                tool_result=prev_worker_input.tool_result,
            )
            logger.info(f"[supervisor] REJECT after {context[Ctx.LOOPS_USED]} transitions")
            return State.WORK

        raise RuntimeError("Critic decision must be ACCEPT or REJECT.")
