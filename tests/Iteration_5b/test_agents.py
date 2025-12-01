from dataclasses import dataclass

import pytest
from pydantic import ValidationError

from Iteration_5b.compute import compute
from Iteration_5b.schemas import (
    CriticInput,
    CriticOutput,
    Decision,
    PlannerInput,
    PlannerOutput,
    Result,
    Task,
    WorkerInput,
    WorkerOutput,
)
from Iteration_5b.supervisor import Supervisor


# --------------------------------------------------
# Test atomic schemas
# --------------------------------------------------

def test_result_schema_accepts_valid():
    r = Result(value=42)
    assert r.value == 42


def test_result_schema_rejects_invalid():
    with pytest.raises(ValidationError):
        Result(value="not-an-int")


def test_decision_requires_feedback_on_reject():
    with pytest.raises(ValueError):
        Decision(decision="REJECT", feedback=None)


def test_decision_accepts_lightweight_on_accept():
    d = Decision(decision="ACCEPT", feedback=None)
    assert d.decision == "ACCEPT"


# --------------------------------------------------
# Deterministic compute tool
# --------------------------------------------------

def test_compute_add():
    t = Task(op="ADD", a=2, b=3)
    assert compute(op=t.op, a=t.a, b=t.b) == 5

def test_compute_sub():
    assert compute(op="SUB", a=4, b=5) == -1

def test_compute_mul():
    assert compute(op="MUL", a=4, b=5) == 20

def test_compute_invalid_op():
    with pytest.raises(ValueError):
        compute(op="DIV", a=4, b=2)


# --------------------------------------------------
# Worker output schema (single branch)
# --------------------------------------------------

def test_worker_output_valid():
    payload = {"result": {"value": 99}}
    wo = WorkerOutput.model_validate(payload)
    assert wo.result.value == 99


def test_worker_output_requires_result():
    with pytest.raises(ValidationError):
        WorkerOutput.model_validate({})


# --------------------------------------------------
# Supervisor loop with stub agents (no network)
# --------------------------------------------------

@dataclass
class StubAgent:
    name: str
    input_schema: type
    output_schema: type
    responder: callable

    def __call__(self, user_input: str) -> str:
        return self.responder(user_input)


def test_supervisor_plan_worker_critic_loop():
    # Planner: emit a fixed task
    def planner_responder(_: str) -> str:
        return PlannerOutput(op="ADD", a=1, b=2).model_dump_json()

    # Worker: compute the result deterministically
    def worker_responder(user_input: str) -> str:
        win = WorkerInput.model_validate_json(user_input)
        value = compute(op=win.task.op, a=win.task.a, b=win.task.b)
        return WorkerOutput(result=Result(value=value)).model_dump_json()

    # Critic: recompute and judge
    def critic_responder(user_input: str) -> str:
        cin = CriticInput.model_validate_json(user_input)
        expected = compute(op=cin.plan.op, a=cin.plan.a, b=cin.plan.b)
        decision = "ACCEPT" if cin.worker_answer.value == expected else "REJECT"
        feedback = "correct" if decision == "ACCEPT" else f"expected {expected}"
        return Decision(decision=decision, feedback=feedback).model_dump_json()

    planner = StubAgent(
        name="Planner",
        input_schema=PlannerInput,
        output_schema=PlannerOutput,
        responder=planner_responder,
    )
    worker = StubAgent(
        name="Worker",
        input_schema=WorkerInput,
        output_schema=WorkerOutput,
        responder=worker_responder,
    )
    critic = StubAgent(
        name="Critic",
        input_schema=CriticInput,
        output_schema=CriticOutput,
        responder=critic_responder,
    )

    sup = Supervisor(
        planner=planner,
        worker=worker,
        critic=critic,
        max_retries=1,
        max_loops=2,
    )

    result = sup.run_once()
    assert result["decision"].decision == "ACCEPT"
    assert isinstance(result["plan"], Task)
    assert result["result"].result.value == 3
