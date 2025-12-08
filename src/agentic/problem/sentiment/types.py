from typing import Literal

from pydantic import BaseModel, Field

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


class SentimentTask(BaseModel):
    """Sentiment classification task."""
    text: str = Field(..., max_length=280)
    target_sentiment: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]


class Result(BaseModel):
    """Sentiment label produced by Worker."""
    sentiment: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]


class SentimentPlannerInput(PlannerInput[SentimentTask, Result]):
    """Planner context for sentiment tasks."""
    previous_task: SentimentTask | None = None
    feedback: str | None = None
    random_seed: int | str | None = None
    project_state: ProjectState | None = None


# Bind generics to domain
SentimentPlannerOutput = PlannerOutput[SentimentTask]
SentimentWorkerInput = WorkerInput[SentimentTask, Result]
SentimentWorkerOutput = WorkerOutput[Result]


class SentimentCriticInput(CriticInput[SentimentTask, Result]):
    project_state: ProjectState | None = None


SentimentCriticOutput = Decision

# Dispatcher binding for this domain
SentimentDispatcher = AgentDispatcher[SentimentTask, Result, Decision]
