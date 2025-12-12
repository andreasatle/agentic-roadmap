from openai import OpenAI
from pydantic import BaseModel

from agentic.tool_registry import ToolRegistry
from domain.sentiment.types import SentimentDispatcher
from domain.sentiment.planner import make_planner
from domain.sentiment.worker import make_worker
from domain.sentiment.critic import make_critic
from agentic.common.domain_state import StatelessProblemState

class SentimentContextState(StatelessProblemState):
    pass

def make_agent_dispatcher(
    client: OpenAI,
    model: str = "gpt-4.1-mini",
    max_retries: int = 3,
) -> SentimentDispatcher:
    planner = make_planner(client, model=model)
    worker = make_worker(client, model=model)
    critic = make_critic(client, model=model)
    return SentimentDispatcher(
        max_retries=max_retries,
        planner=planner,
        workers={"sentiment-worker": worker},
        critic=critic,
        domain_name="sentiment",
    )


def make_tool_registry() -> ToolRegistry:
    # Sentiment domain has no tools; return an empty registry for interface parity.
    return ToolRegistry()


def problem_state_cls() -> type[BaseModel]:
    return SentimentContextState
