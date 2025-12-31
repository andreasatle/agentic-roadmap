from agentic.tool_registry import ToolRegistry
from domain.sentiment.types import SentimentDispatcher
from domain.sentiment.planner import make_planner
from domain.sentiment.worker import make_worker
from domain.sentiment.critic import make_critic
def make_agent_dispatcher(
    model: str = "gpt-4.1-mini",
    max_retries: int = 3,
) -> SentimentDispatcher:
    planner = make_planner(model=model)
    worker = make_worker(model=model)
    critic = make_critic(model=model)
    return SentimentDispatcher(
        max_retries=max_retries,
        planner=planner,
        workers={"sentiment-worker": worker},
        critic=critic,
    )


def make_tool_registry() -> ToolRegistry:
    # Sentiment domain has no tools; return an empty registry for interface parity.
    return ToolRegistry()
