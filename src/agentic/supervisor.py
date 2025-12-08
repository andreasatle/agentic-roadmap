from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

from agentic.schemas import WorkerInput, Decision, ProjectState
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
    planner_defaults: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._handlers: dict[State, Callable[[SupervisorContext], State]] = {
            State.PLAN: self._handle_plan,
            State.WORK: self._handle_work,
            State.TOOL: self._handle_tool,
            State.CRITIC: self._handle_critic,
        }

    def __call__(self) -> dict:
        """
        Explicit FSM over PLAN → WORK → TOOL/CRITIC → END.
        Each agent/tool invocation is a state transition.
        """
        context = SupervisorContext(trace=[])
        context.project_state = ProjectState()
        self._current_project_state = context.project_state
        state = State.PLAN

        while state != State.END and context.loops_used < self.max_loops:
            handler = self._handlers.get(state)
            if handler is None:
                raise RuntimeError(f"Unknown supervisor state: {state}")
            context.loops_used += 1
            context.project_state.cycle += 1
            state = handler(context)

        if state != State.END:
            raise RuntimeError("Supervisor exited without reaching END state.")

        context.trace.append(
            {
                "state": State.END,
                "result": context.final_result,
                "decision": context.decision,
                "loops_used": context.loops_used,
                "project_state": context.project_state,
            }
        )
        return {
            "plan": context.plan,
            "result": context.final_result,
            "decision": context.decision,
            "loops_used": context.loops_used,
            "project_state": context.project_state,
        }

    def _handle_plan(self, context: SupervisorContext) -> State:
        planner_input_cls = self.dispatcher.planner.input_schema
        planner_kwargs: dict[str, Any] = dict(self.planner_defaults or {})
        planner_kwargs.update(
            feedback=context.planner_feedback,
            previous_task=context.previous_plan,
            previous_worker_id=context.previous_worker_id,
        )
        if "project_state" in planner_input_cls.model_fields:
            planner_kwargs["project_state"] = context.project_state

        required_fields = getattr(planner_input_cls, "model_fields", {})
        if "project_description" in required_fields and not planner_kwargs.get("project_description"):
            raise RuntimeError("Coder domain requires planner_defaults['project_description'] to be set.")

        planner_input = planner_input_cls(**planner_kwargs)
        try:
            planner_response = self.dispatcher.plan(planner_input)
        except RuntimeError as e:
            # Planner failed (e.g., invalid worker routing). Route through critic.
            context.feedback = str(e)
            context.plan = None
            context.worker_id = None
            context.worker_input = None
            context.last_stage = "plan"
            context.trace.append(
                {
                    "state": State.PLAN,
                    "agent_id": "Planner",
                    "call_id": None,
                    "tool_name": None,
                    "input": None,
                    "output": None,
                    "error": str(e),
                }
            )
            context.project_state.history.append(
                {
                    "state": State.PLAN.name,
                    "worker_id": context.worker_id,
                    "plan": context.plan,
                    "result": None,
                    "decision": None,
                }
            )
            context.critic_input = self._build_critic_input(
                plan={},
                worker_answer=None,
                worker_id=None,
            )
            return State.CRITIC

        logger.debug(f"[supervisor] PLAN call_id={planner_response.call_id}")
        planner_output = planner_response.output
        context.plan = planner_output.task
        context.project_state.last_plan = (
            context.plan.model_dump() if hasattr(context.plan, "model_dump") else context.plan
        )
        context.worker_id = planner_output.worker_id
        context.previous_plan = planner_output.task
        context.previous_worker_id = planner_output.worker_id
        context.planner_feedback = None
        context.worker_input = WorkerInput(task=context.plan)
        context.last_stage = "plan"
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
        context.project_state.history.append(
            {
                "state": State.PLAN.name,
                "worker_id": context.worker_id,
                "plan": context.plan.model_dump() if hasattr(context.plan, "model_dump") else context.plan,
                "result": None,
                "decision": None,
            }
        )
        return State.WORK

    def _handle_work(self, context: SupervisorContext) -> State:
        if context.worker_input is None:
            raise RuntimeError("WORK state reached without worker_input in context.")
        if context.worker_id is None:
            raise RuntimeError("WORK state reached without worker_id in context.")
        if context.plan is None:
            raise RuntimeError("WORK state reached without plan in context.")

        task = context.plan
        worker_id = context.worker_id
        if not self.dispatcher.validate_worker_routing(task, worker_id):
            context.critic_input = self._build_critic_input(
                plan=task,
                worker_answer=None,
                worker_id=worker_id,
            )
            context.decision = Decision(
                decision="REJECT",
                feedback=f"Worker '{worker_id}' is not valid for the proposed plan",
            )
            context.project_state.history.append(
                {
                    "state": State.WORK.name,
                    "worker_id": context.worker_id,
                    "plan": context.plan.model_dump() if hasattr(context.plan, "model_dump") else context.plan,
                    "result": None,
                    "decision": context.decision.model_dump() if hasattr(context.decision, "model_dump") else context.decision,
                }
            )
            return State.CRITIC

        worker_response = self.dispatcher.work(context.worker_id, context.worker_input)
        worker_output = worker_response.output
        context.worker_output = worker_output
        context.last_stage = "work"
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
            context.project_state.last_result = (
                context.worker_result.model_dump() if hasattr(context.worker_result, "model_dump") else context.worker_result
            )
            context.critic_input = self._build_critic_input(
                plan=context.plan,
                worker_answer=worker_output.result,
                worker_id=context.worker_id,
            )
            context.project_state.history.append(
                {
                    "state": State.WORK.name,
                    "worker_id": context.worker_id,
                    "plan": context.plan.model_dump() if hasattr(context.plan, "model_dump") else context.plan,
                    "result": context.worker_result.model_dump() if hasattr(context.worker_result, "model_dump") else context.worker_result,
                    "decision": None,
                }
            )
            return State.CRITIC

        if worker_output.tool_request is not None:
            context.tool_request = worker_output.tool_request
            context.project_state.history.append(
                {
                    "state": State.WORK.name,
                    "worker_id": context.worker_id,
                    "plan": context.plan.model_dump() if hasattr(context.plan, "model_dump") else context.plan,
                    "result": context.worker_result.model_dump() if hasattr(context.worker_result, "model_dump") else context.worker_result,
                    "decision": None,
                }
            )
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
        context.project_state.history.append(
            {
                "state": State.TOOL.name,
                "worker_id": context.worker_id,
                "plan": context.plan.model_dump() if hasattr(context.plan, "model_dump") else context.plan,
                "result": context.worker_result.model_dump() if hasattr(context.worker_result, "model_dump") else context.worker_result,
                "decision": None,
            }
        )
        return State.WORK

    def _handle_critic(self, context: SupervisorContext) -> State:
        if context.critic_input is None:
            raise RuntimeError("CRITIC state reached without critic_input in context.")

        critic_response = self.dispatcher.critique(context.critic_input)
        decision = critic_response.output
        context.decision = decision
        context.project_state.last_decision = (
            context.decision.model_dump() if hasattr(context.decision, "model_dump") else context.decision
        )
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
        context.project_state.history.append(
            {
                "state": State.CRITIC.name,
                "worker_id": context.worker_id,
                "plan": context.plan.model_dump() if hasattr(context.plan, "model_dump") else context.plan,
                "result": context.worker_result.model_dump() if hasattr(context.worker_result, "model_dump") else context.worker_result,
                "decision": context.decision.model_dump() if hasattr(context.decision, "model_dump") else context.decision,
            }
        )

        if decision.decision == "ACCEPT":
            context.final_result = context.worker_result
            context.final_output = context.worker_output
            logger.info(f"[supervisor] ACCEPT after {context.loops_used} transitions")
            return State.END

        if decision.decision == "REJECT":
            prev_worker_input = context.worker_input
            if context.last_stage == "plan" or context.plan is None or prev_worker_input is None:
                context.planner_feedback = decision.feedback
                # Planner failed, retry planning
                logger.info(f"[supervisor] REJECT after {context.loops_used} transitions (replanning)")
                return State.PLAN
            context.feedback = decision.feedback
            context.worker_input = WorkerInput(
                task=prev_worker_input.task,
                previous_result=prev_worker_input.previous_result,
                feedback=decision.feedback,
                tool_result=prev_worker_input.tool_result,
            )
            logger.info(f"[supervisor] REJECT after {context.loops_used} transitions")
            return State.WORK

        raise RuntimeError("Critic decision must be ACCEPT or REJECT.")

    def _build_critic_input(self, plan, worker_answer, worker_id):
        critic_input_cls = self.dispatcher.critic.input_schema
        critic_kwargs = {"plan": plan, "worker_answer": worker_answer}
        fields = critic_input_cls.model_fields
        if "worker_id" in fields:
            critic_kwargs["worker_id"] = worker_id or ""
        if "project_description" in fields:
            critic_kwargs["project_description"] = self.planner_defaults.get("project_description", "")
        if "project_state" in fields:
            critic_kwargs["project_state"] = getattr(self, "_current_project_state", None)
        return critic_input_cls(**critic_kwargs)
