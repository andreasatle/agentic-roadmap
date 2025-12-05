from openai import OpenAI

from ...tool_registry import ToolRegistry
from .types import ArithmeticDispatcher, Task
from .planner import make_planner
from .worker import make_worker
from .critic import make_critic
from .tools import compute


def make_agent_dispatcher(
    client: OpenAI,
    model: str = "gpt-4.1-mini",
    max_retries: int = 3,
) -> ArithmeticDispatcher:
    planner = make_planner(client, model=model)
    worker = make_worker(client, model=model)
    critic = make_critic(client, model=model)
    return ArithmeticDispatcher(
        max_retries=max_retries,
        planner=planner,
        worker=worker,
        critic=critic,
    )


def make_tool_registry() -> ToolRegistry:
    tool_registry = ToolRegistry()
    tool_registry.register("compute", "A deterministic arithmetic tool.", compute, Task)
    return tool_registry
