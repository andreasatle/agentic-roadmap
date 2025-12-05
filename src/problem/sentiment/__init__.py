from .types import (
    Task,
    Result,
    SentimentPlannerInput,
    SentimentPlannerOutput,
    SentimentWorkerInput,
    SentimentWorkerOutput,
    SentimentCriticInput,
    SentimentCriticOutput,
    SentimentDispatcher,
)
from .planner import make_planner
from .worker import make_worker
from .critic import make_critic
from ...tool_registry import ToolRegistry


def make_agent_dispatcher(client, model: str = "gpt-4.1-mini", max_retries: int = 3) -> SentimentDispatcher:
    planner = make_planner(client, model=model)
    worker = make_worker(client, model=model)
    critic = make_critic(client, model=model)
    return SentimentDispatcher(
        max_retries=max_retries,
        planner=planner,
        worker=worker,
        critic=critic,
    )


def make_tool_registry() -> ToolRegistry:
    # Sentiment domain has no tools; return an empty registry for interface parity.
    return ToolRegistry()

__all__ = [
    "Task",
    "Result",
    "SentimentPlannerInput",
    "SentimentPlannerOutput",
    "SentimentWorkerInput",
    "SentimentWorkerOutput",
    "SentimentCriticInput",
    "SentimentCriticOutput",
    "SentimentDispatcher",
    "make_agent_dispatcher",
    "make_planner",
    "make_worker",
    "make_critic",
    "make_tool_registry",
]
