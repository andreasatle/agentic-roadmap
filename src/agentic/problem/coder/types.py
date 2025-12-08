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
    ProjectState,
)


class CodeTask(BaseModel):
    """Decomposed coding subtask derived from the user project."""
    language: Literal["python", "javascript"]
    specification: str = Field(..., max_length=300)
    requirements: list[str] = Field(..., min_length=1, max_length=5)


class CodeResult(BaseModel):
    """Code produced by the worker."""
    code: str


# Bind generics to domain
class CoderPlannerInput(PlannerInput[CodeTask, CodeResult]):
    """Planner context tied to a user-defined project."""
    project_description: str
    previous_task: CodeTask | None = None
    feedback: str | None = None
    previous_worker_id: str | None = None
    random_seed: int | str | None = None
    project_state: ProjectState | None = None


CoderPlannerOutput = PlannerOutput[CodeTask]
CoderWorkerInput = WorkerInput[CodeTask, CodeResult]
CoderWorkerOutput = WorkerOutput[CodeResult]


class CoderCriticInput(CriticInput[CodeTask, CodeResult]):
    """Critic sees the plan, worker answer, and the overarching project."""
    project_description: str
    project_state: ProjectState | None = None


CoderCriticOutput = Decision

# Dispatcher binding for this domain
CoderDispatcher = AgentDispatcher[CodeTask, CodeResult, Decision]
