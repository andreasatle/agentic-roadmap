from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from agentic.agent_dispatcher import AgentDispatcher
from agentic.schemas import Decision, PlannerOutput, WorkerInput, WorkerOutput, _normalize_for_json, Feedback


class CodeTask(BaseModel):
    """Decomposed coding subtask derived from the user project."""
    language: Literal["python", "javascript"]
    specification: str = Field(..., max_length=300)
    requirements: list[str] = Field(..., min_length=1, max_length=5)


class CodeResult(BaseModel):
    """Code produced by the worker."""
    code: str


# Bind generics to domain
class CoderPlannerInput(BaseModel):
    """Planner context tied to a user-defined project."""
    model_config = ConfigDict(extra="allow")

    project_description: str
    previous_task: CodeTask | None = None
    feedback: Feedback | None = None
    previous_worker_id: str | None = None
    random_seed: int | str | None = None

    def to_llm(self) -> dict:
        raw = self.model_dump()
        normalized = _normalize_for_json(raw)
        return normalized


CoderPlannerOutput = PlannerOutput[CodeTask]
CoderWorkerInput = WorkerInput[CodeTask, CodeResult]
CoderWorkerOutput = WorkerOutput[CodeResult]


class CoderCriticInput(BaseModel):
    """Critic sees the plan, worker answer, and the overarching project."""
    model_config = ConfigDict(extra="allow")

    project_description: str
    plan: CodeTask
    worker_answer: CodeResult | None
    worker_id: str | None = None

    def to_llm(self) -> dict:
        raw = self.model_dump()
        normalized = _normalize_for_json(raw)
        return normalized


CoderCriticOutput = Decision

# Dispatcher binding for this domain
CoderDispatcher = AgentDispatcher[CodeTask, CodeResult, Decision]
