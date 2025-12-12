from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable
from pydantic import BaseModel

from agentic.schemas import WorkerInput, Decision, ProjectState, Feedback
from agentic.tool_registry import ToolRegistry
from agentic.logging_config import get_logger
from agentic.agent_dispatcher import AgentDispatcher
from agentic.supervisor_types import SupervisorState as State, SupervisorContext
from agentic.supervisor_result import SupervisorRunResult
logger = get_logger("agentic.supervisor")


@dataclass
class Supervisor:
    dispatcher: AgentDispatcher
    tool_registry: ToolRegistry
    problem_state_cls: Callable[[], type[BaseModel]]
    domain_state: BaseModel | None
    max_loops: int = 5
    planner_defaults: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._handlers: dict[State, Callable[[SupervisorContext], State]] = {
            State.PLAN: self._handle_plan,
            State.WORK: self._handle_work,
            State.TOOL: self._handle_tool,
            State.CRITIC: self._handle_critic,
        }

    def __call__(self) -> SupervisorRunResult:
        """
        Explicit FSM over PLAN → WORK → TOOL/CRITIC → END.
        Each agent/tool invocation is a state transition.
        Returns a structured SupervisorRunResult.
        """
        context = SupervisorContext(trace=[])
        context.project_state = ProjectState()
        context.project_state.domain_state = self.domain_state
        self._current_project_state = context.project_state
        state = State.PLAN

        while state != State.END and context.loops_used < self.max_loops:
            handler = self._handlers.get(state)
            if handler is None:
                raise RuntimeError(f"Unknown supervisor state: {state}")
            context.loops_used += 1
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
        return SupervisorRunResult(
            plan=context.plan,
            result=context.final_result,
            decision=context.decision,
            loops_used=context.loops_used,
            project_state=context.project_state,
            trace=context.trace or [],
        )

    def _make_snapshot(self, context):
        snapshot = {}

        # Global project summary
        domain_state_obj = getattr(context.project_state, "domain_state", None)
        domain_snapshot = domain_state_obj.snapshot_for_llm() if domain_state_obj is not None else None
        project_snapshot = {
            "domain_state": domain_snapshot,
            "last_plan": context.project_state.last_plan,
            "last_result": context.project_state.last_result,
            "last_decision": context.project_state.last_decision,
        }
        if project_snapshot:
            snapshot.update(project_snapshot)

        # Return None if no information is present
        return snapshot or None

    def _handle_plan(self, context: SupervisorContext) -> State:
        planner_input_cls = self.dispatcher.planner.input_schema
        planner_kwargs: dict[str, Any] = dict(self.planner_defaults or {})
        planner_feedback = context.planner_feedback
        if isinstance(planner_feedback, str):
            planner_feedback = Feedback(kind="OTHER", message=planner_feedback)
        planner_kwargs.update(
            feedback=planner_feedback,
            previous_task=context.previous_plan,
            previous_worker_id=context.previous_worker_id,
        )

        required_fields = getattr(planner_input_cls, "model_fields", {})
        if "project_description" in required_fields and not planner_kwargs.get("project_description"):
            raise RuntimeError("Coder domain requires planner_defaults['project_description'] to be set.")

        planner_input = planner_input_cls(**planner_kwargs)
        snapshot = self._make_snapshot(context)
        try:
            planner_response = self.dispatcher.plan(planner_input, snapshot=snapshot)
        except RuntimeError as e:
            context.planner_feedback = Feedback(kind="OTHER", message=str(e))
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
            return State.PLAN

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
        context.worker_input = WorkerInput(
            task=context.plan,
        )
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
            return State.CRITIC

        snapshot = self._make_snapshot(context)
        worker_response = self.dispatcher.work(context.worker_id, context.worker_input, snapshot=snapshot)
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

        snapshot = self._make_snapshot(context)
        critic_response = self.dispatcher.critique(context.critic_input, snapshot=snapshot)
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
        if decision.decision == "ACCEPT":
            context.final_result = context.worker_result
            context.final_output = context.worker_output
            prev_state = context.project_state.domain_state
            if prev_state is None:
                raise RuntimeError("Domain state must be provided to Supervisor.")
            new_state = prev_state.update(context.plan, context.worker_result)
            context.project_state.domain_state = new_state
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
        return critic_input_cls(**critic_kwargs)
