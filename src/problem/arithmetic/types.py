from typing import Literal
from pydantic import BaseModel, Field

from ...schemas import (
    Decision,
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
    CriticInput,
)
from ...agent_dispatcher import AgentDispatcher

class Task(BaseModel):
    """A well-bounded arithmetic task."""
    op: Literal["ADD", "SUB", "MUL"]
    a: int = Field(..., ge=1, le=20)
    b: int = Field(..., ge=1, le=20)

class Result(BaseModel):
    """A numeric answer produced by Worker."""
    value: int = Field(..., ge=-10_000, le=10_000)

# Bind generics to domain
ArithmeticPlannerInput = PlannerInput[Task, Result]
ArithmeticPlannerOutput = PlannerOutput[Task]
ArithmeticWorkerInput = WorkerInput[Task, Result]
ArithmeticWorkerOutput = WorkerOutput[Result, Task]
ArithmeticCriticInput = CriticInput[Task, Result]
ArithmeticCriticOutput = Decision

# Dispatcher binding for this domain
ArithmeticDispatcher = AgentDispatcher[Task, Result, Decision]
