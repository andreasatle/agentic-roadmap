
import pytest
from pydantic import ValidationError

from agentic.controller import Controller, ControllerRequest, ControllerDomainInput
from agentic.tool_registry import ToolRegistry
from experiments.arithmetic.types import (
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
        max_retries=1,
    )

    controller = Controller(
        dispatcher=dispatcher,
        tool_registry=ToolRegistry(),
    )

    output = controller(
        ControllerRequest(
            domain=ControllerDomainInput(
                task=task,
            ),
        )
    )

    summary_before = output.model_dump()

    def outer_controller(result):
        return {
            "has_task": result.task is not None,
            "has_worker_output": result.worker_output is not None,
            "decision": result.critic_decision.get("decision") if isinstance(result.critic_decision, dict) else getattr(result.critic_decision, "decision", None),
            "trace_length": len(result.trace or []),
        }

    summary = outer_controller(output)

    assert summary["has_task"]
    assert summary["has_worker_output"]
    assert summary["decision"] == "ACCEPT"
    assert summary["trace_length"] >= 1
    assert output.model_dump() == summary_before

    with pytest.raises(ValidationError):
        output.task = None
