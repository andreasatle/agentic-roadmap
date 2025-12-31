from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from agentic.agent_dispatcher import AgentDispatcher
from agentic.schemas import Decision, PlannerOutput, WorkerInput, WorkerOutput


class SentimentTask(BaseModel):
    """Sentiment classification task."""
    text: str = Field(..., max_length=280)
    target_sentiment: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]


class Result(BaseModel):
    """Sentiment label produced by Worker."""
    sentiment: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]


class SentimentPlannerInput(BaseModel):
    """Planner context for sentiment tasks."""
    model_config = ConfigDict(extra="allow")

    task: SentimentTask


# Bind generics to domain
SentimentPlannerOutput = PlannerOutput[SentimentTask]
SentimentWorkerInput = WorkerInput[SentimentTask, Result]
SentimentWorkerOutput = WorkerOutput[Result]


class SentimentCriticInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    plan: SentimentTask
    worker_answer: Result | None
    worker_id: str | None = None

    def to_llm(self) -> dict:
        raw = self.model_dump()
        normalized = _normalize_for_json(raw)
        return normalized


SentimentCriticOutput = Decision

# Dispatcher binding for this domain
SentimentDispatcher = AgentDispatcher[SentimentTask, Result, Decision]
