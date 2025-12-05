from typing import Literal

from pydantic import BaseModel, Field

from ...agent_dispatcher import AgentDispatcher
from ...schemas import (
    Decision,
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
    CriticInput,
)


class Task(BaseModel):
    """Sentiment classification task."""
    text: str = Field(..., max_length=280)


class Result(BaseModel):
    """Sentiment label produced by Worker."""
    sentiment: Literal["POSITIVE", "NEGATIVE", "NEUTRAL"]


# Bind generics to domain
SentimentPlannerInput = PlannerInput[Task, Result]
SentimentPlannerOutput = PlannerOutput[Task]
SentimentWorkerInput = WorkerInput[Task, Result]
SentimentWorkerOutput = WorkerOutput[Result, Task]
SentimentCriticInput = CriticInput[Task, Result]
SentimentCriticOutput = Decision

# Dispatcher binding for this domain
SentimentDispatcher = AgentDispatcher[Task, Result, Decision]
