from pydantic import BaseModel, Field
from typing import Literal

from agentic.agent_dispatcher import AgentDispatcher
from agentic.schemas import (
    Decision,
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
    CriticInput,
)


class CodeTask(BaseModel):
    """Small coding problem for the worker to implement."""
    language: Literal["python", "javascript"]
    specification: str = Field(..., max_length=300)
    requirements: list[str] = Field(..., min_length=1, max_length=5)


class CodeResult(BaseModel):
    """Code produced by the worker."""
    code: str


# Bind generics to domain
CoderPlannerInput = PlannerInput[CodeTask, CodeResult]
CoderPlannerOutput = PlannerOutput[CodeTask]
CoderWorkerInput = WorkerInput[CodeTask, CodeResult]
CoderWorkerOutput = WorkerOutput[CodeResult]
CoderCriticInput = CriticInput[CodeTask, CodeResult]
CoderCriticOutput = Decision

# Dispatcher binding for this domain
CoderDispatcher = AgentDispatcher[CodeTask, CodeResult, Decision]
