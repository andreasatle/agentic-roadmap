from __future__ import annotations

import pytest
from pydantic import ValidationError

from agentic.supervisor import Supervisor, SupervisorRequest, SupervisorControlInput, SupervisorDomainInput
from agentic.tool_registry import ToolRegistry
from agentic.schemas import ProjectState
from domain.arithmetic.types import (
    ArithmeticCriticInput,
    ArithmeticCriticOutput,
    ArithmeticPlannerInput,
    ArithmeticPlannerOutput,
    ArithmeticResult,
    ArithmeticTask,
    ArithmeticWorkerInput,
    ArithmeticWorkerOutput,
    ArithmeticDispatcher,
)
from domain.arithmetic.factory import ArithmeticContentState


class DummyAgent:
    def __init__(self, name, input_schema, output_model):
        self.id = name
        self.name = name
        self.input_schema = input_schema
        self.output_schema = type(output_model)
        self._payload = output_model.model_dump_json()

    def __call__(self, _input_json: str) -> str:
        return self._payload


def test_supervisor_output_is_immutable_and_serializable():
    planner_output = ArithmeticPlannerOutput(
        task=ArithmeticTask(op="ADD", a=1, b=2),
        worker_id="worker_addsub",
    )
    worker_output = ArithmeticWorkerOutput(result=ArithmeticResult(value=3))
    critic_output = ArithmeticCriticOutput(decision="ACCEPT")

    planner_agent = DummyAgent("planner", input_schema=ArithmeticPlannerInput, output_model=planner_output)
    worker_agent = DummyAgent("worker_addsub", input_schema=ArithmeticWorkerInput, output_model=worker_output)
    critic_agent = DummyAgent("critic", input_schema=ArithmeticCriticInput, output_model=critic_output)
    task = ArithmeticTask(op="ADD", a=1, b=2)

    dispatcher = ArithmeticDispatcher(
        planner=planner_agent,
        workers={"worker_addsub": worker_agent},
        critic=critic_agent,
        domain_name="arithmetic",
        max_retries=1,
    )

    project_state = ProjectState()
    project_state.domain_state = ArithmeticContentState()
    supervisor = Supervisor(
        dispatcher=dispatcher,
        tool_registry=ToolRegistry(),
        project_state=project_state,
        max_loops=3,
        problem_state_cls=lambda: ArithmeticContentState,
    )

    output = supervisor.handle(
        SupervisorRequest(
            control=SupervisorControlInput(max_loops=3),
            domain=SupervisorDomainInput(
                domain_state=project_state.domain_state,
                task=task,
            ),
        )
    )

    summary_before = output.model_dump()

    def outer_controller(result):
        return {
            "has_plan": result.plan is not None,
            "has_result": result.result is not None,
            "decision": result.decision.get("decision") if isinstance(result.decision, dict) else getattr(result.decision, "decision", None),
            "trace_length": len(result.trace),
            "project_state_present": result.project_state is not None,
        }

    summary = outer_controller(output)

    assert summary["has_plan"]
    assert summary["has_result"]
    assert summary["decision"] == "ACCEPT"
    assert summary["trace_length"] >= 1
    assert summary["project_state_present"]
    assert output.model_dump() == summary_before

    with pytest.raises(ValidationError):
        output.plan = None
