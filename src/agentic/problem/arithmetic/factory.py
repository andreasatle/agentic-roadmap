from openai import OpenAI

from agentic.tool_registry import ToolRegistry
from agentic.problem.arithmetic.types import ArithmeticDispatcher, Task
from agentic.problem.arithmetic.planner import make_planner
from agentic.problem.arithmetic.worker import make_worker
from agentic.problem.arithmetic.critic import make_critic
from agentic.problem.arithmetic.tools import compute


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
        workers={"arithmetic-worker": worker},
        critic=critic,
    )


def make_tool_registry() -> ToolRegistry:
    tool_registry = ToolRegistry()
    tool_registry.register("compute", "A deterministic arithmetic tool.", compute, Task)
    return tool_registry
