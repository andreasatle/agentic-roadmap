"""
Controller contract (authoritative test oracle):
- The Controller is a pure executor.
- It executes exactly one task per request.
- It does not create, advance, or decide tasks, manage workflow, or loop for progress.
- It returns a single immutable response representing one execution attempt.
- Retry limits are enforced externally; Controller execution is atomic and finite per call.
Any behavior diverging from this contract is a bug.
"""
from typing import Any, Self
from pydantic import BaseModel, ConfigDict, model_validator

from agentic.schemas import WorkerInput
from agentic.tool_registry import ToolRegistry
from agentic.agent_dispatcher import AgentDispatcher
from agentic.controller_types import ControllerState as State


class ControllerDomainInput(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    task: Any

    @model_validator(mode="after")
    def validate_task(self) -> Self:
        if self.task is None:
            raise ValueError("ControllerRequest requires exactly one task.")
        if isinstance(self.task, (list, tuple, set)):
            raise ValueError("ControllerRequest accepts exactly one task, not a collection.")
        return self


class ControllerRequest(BaseModel):
    """Pure single-pass request: exactly one explicit task."""
    domain: ControllerDomainInput


class ControllerResponse(BaseModel):
    """ControllerResponse is an immutable event representing one execution attempt."""

    model_config = ConfigDict(frozen=True)

    task: Any
    worker_id: str
    worker_output: Any | None
    critic_decision: Any | None
    trace: list[dict] | None = None


class Controller:
    def __init__(
        self,
        *,
        dispatcher: AgentDispatcher,
        tool_registry: ToolRegistry,
    ) -> None:
        self.dispatcher = dispatcher
        self.tool_registry = tool_registry

    def __call__(self, request: ControllerRequest) -> ControllerResponse:
        """
        Explicit FSM over PLAN → WORK → TOOL/CRITIC → END.
        Each agent/tool invocation is a state transition.
        Returns a structured ControllerResponse.
        """
        def _to_event(value):
            if hasattr(value, "model_dump"):
                return _to_event(value.model_dump())
            if isinstance(value, dict):
                return {k: _to_event(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_to_event(v) for v in value]
            if isinstance(value, tuple):
                return [_to_event(v) for v in value]
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            raise TypeError(f"Non-serializable type: {type(value).__name__}")

        request_task = request.domain.task
        if request_task is None:
            raise RuntimeError("ControllerRequest must include a task.")
        trace: list[dict] = []

        # PLAN
        planner_input_cls = self.dispatcher.planner.input_schema
        planner_kwargs = {}
        if "task" in getattr(planner_input_cls, "model_fields", {}):
            planner_kwargs["task"] = request_task
        planner_input = planner_input_cls(**planner_kwargs)
        planner_response = self.dispatcher.plan(planner_input)
        planner_output = planner_response.output
        if getattr(planner_output, "task", None) != request_task:
            raise RuntimeError("Planner output task did not match requested task.")
        worker_id = planner_output.worker_id
        worker_agent = self.dispatcher.workers.get(worker_id)
        worker_input_cls = worker_agent.input_schema if worker_agent else WorkerInput
        worker_input = worker_input_cls(task=request_task)
        trace.append(
            {
                "state": State.PLAN.name,
                "agent_id": planner_response.agent_id,
                "call_id": planner_response.call_id,
                "tool_name": None,
                "input": None,
                "output": planner_response.output,
            }
        )

        # WORK
        worker_response = self.dispatcher.work(worker_id, worker_input)
        worker_output = worker_response.output
        worker_result = worker_output.result
        trace.append(
            {
                "state": State.WORK.name,
                "agent_id": worker_response.agent_id,
                "call_id": worker_response.call_id,
                "tool_name": None,
                "input": worker_input,
                "output": worker_output,
            }
        )

        # TOOL (single pass)
        if worker_output.tool_request is not None:
            request_tool = worker_output.tool_request
            entry = self.tool_registry.get(request_tool.tool_name)
            if entry is None:
                raise RuntimeError(f"Unknown tool: {request_tool.tool_name}")
            _, func, arg_type = entry
            if not isinstance(request_tool.args, arg_type):
                raise TypeError(f"Args for '{request_tool.tool_name}' must be {arg_type.__name__}")
            tool_result = func(request_tool.args)
            trace.append(
                {
                    "state": State.TOOL.name,
                    "agent_id": None,
                    "call_id": None,
                    "tool_name": request_tool.tool_name,
                    "input": request_tool.args,
                    "output": tool_result,
                }
            )
            worker_input = worker_input_cls(
                task=worker_input.task,
                previous_result=worker_input.previous_result,
                feedback=worker_input.feedback,
                tool_result=tool_result,
            )
            worker_response = self.dispatcher.work(worker_id, worker_input)
            worker_output = worker_response.output
            worker_result = worker_output.result
            trace.append(
                {
                    "state": State.WORK.name,
                    "agent_id": worker_response.agent_id,
                    "call_id": worker_response.call_id,
                    "tool_name": None,
                    "input": worker_input,
                    "output": worker_output,
                }
            )
            if worker_output.tool_request is not None:
                raise RuntimeError("Worker requested multiple tool invocations; not supported in atomic mode.")

        if worker_result is None:
            raise RuntimeError("WorkerOutput violated 'exactly one branch' invariant.")

        # CRITIC
        critic_input = self._build_critic_input(
            plan=request_task,
            worker_answer=worker_result,
            worker_id=worker_id,
        )
        critic_response = self.dispatcher.critique(critic_input)
        decision = critic_response.output
        trace.append(
            {
                "state": State.CRITIC.name,
                "agent_id": critic_response.agent_id,
                "call_id": critic_response.call_id,
                "tool_name": None,
                "input": critic_input,
                "output": critic_response.output,
            }
        )

        trace.append(
            {
                "state": State.END.name,
                "decision": decision,
            }
        )
        return ControllerResponse(
            task=_to_event(request_task),
            worker_id=_to_event(worker_id),
            worker_output=_to_event(worker_output),
            critic_decision=_to_event(decision),
            trace=[_to_event(entry) for entry in trace] or None,
        )

    # Legacy snapshot and handler methods removed; execution is inline in handle().

    def _build_critic_input(self, plan, worker_answer, worker_id):
        critic_input_cls = self.dispatcher.critic.input_schema
        critic_kwargs = {"plan": plan, "worker_answer": worker_answer}
        fields = critic_input_cls.model_fields
        if "worker_id" in fields:
            critic_kwargs["worker_id"] = worker_id
        for field_name in fields:
            if field_name in critic_kwargs:
                continue
            if hasattr(plan, field_name):
                critic_kwargs[field_name] = getattr(plan, field_name)
        return critic_input_cls(**critic_kwargs)

def run_controller(
    controller_input: ControllerRequest,
    *,
    dispatcher: AgentDispatcher,
    tool_registry: ToolRegistry,
) -> ControllerResponse:
    controller = Controller(
        dispatcher=dispatcher,
        tool_registry=tool_registry,
    )
    return controller(controller_input)
