"""
AnalysisController contract (authoritative test oracle):

- The AnalysisController is a pure planner executor.
- It executes exactly one analysis task per request.
- It does not invoke workers, critics, or tools.
- It does not loop, retry, or advance workflow.
- It returns a single immutable response representing one planning attempt.
- The planner output is treated as the final result.

Any behavior diverging from this contract is a bug.
"""

from typing import Any, Self
from pydantic import BaseModel, ConfigDict, model_validator

from agentic_workflow.agent_dispatcher import AgentDispatcher
from agentic_workflow.controller_types import ControllerState as State


# =========================
# Request / Response types
# =========================

class AnalysisControllerRequest(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    planner_input: BaseModel

    @model_validator(mode="after")
    def validate_planner_input(self) -> Self:
        if self.planner_input is None:
            raise ValueError("AnalysisControllerRequest requires exactly one planner_input.")
        if isinstance(self.planner_input, (list, tuple, set)):
            raise ValueError(
                "AnalysisControllerRequest accepts exactly one planner_input object, not a collection."
            )
        return self


class AnalysisControllerResponse(BaseModel):
    """Immutable result of a single analysis / planning execution."""

    model_config = ConfigDict(frozen=True)

    planner_input: Any
    plan: Any
    trace: list[dict] | None = None


# =========================
# AnalysisController
# =========================

class AnalysisController:
    def __init__(self, *, dispatcher: AgentDispatcher) -> None:
        self.dispatcher = dispatcher

    def __call__(self, request: AnalysisControllerRequest) -> AnalysisControllerResponse:
        def _to_event(value):
            if hasattr(value, "model_dump"):
                return _to_event(value.model_dump())
            if isinstance(value, dict):
                return {k: _to_event(v) for k, v in value.items()}
            if isinstance(value, list):
                return [_to_event(v) for v in value]
            if value is None or isinstance(value, (str, int, float, bool)):
                return value
            raise TypeError(f"Non-serializable type: {type(value).__name__}")

        planner_input = request.planner_input
        planner_input_cls = self.dispatcher.planner.input_schema
        if not isinstance(planner_input, planner_input_cls):
            raise TypeError(
                f"AnalysisController requires planner_input of type {planner_input_cls.__name__}"
            )
        trace: list[dict] = []

        # PLAN (planner-only execution)
        planner_response = self.dispatcher.plan(planner_input)
        planner_output = planner_response.output

        trace.append(
            {
                "state": State.PLAN.name,
                "agent_id": planner_response.agent_id,
                "call_id": planner_response.call_id,
                "input": None,
                "output": planner_output,
            }
        )

        trace.append(
            {
                "state": State.END.name,
            }
        )

        return AnalysisControllerResponse(
            planner_input=_to_event(planner_input),
            plan=_to_event(planner_output),
            trace=[_to_event(entry) for entry in trace],
        )


def run_analysis_controller(
    controller_input: AnalysisControllerRequest,
    *,
    dispatcher: AgentDispatcher,
) -> AnalysisControllerResponse:
    analysis_controller = AnalysisController(dispatcher=dispatcher)
    return analysis_controller(controller_input)
