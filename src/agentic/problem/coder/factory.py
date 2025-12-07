from openai import OpenAI

from agentic.tool_registry import ToolRegistry
from agentic.problem.coder.types import CoderDispatcher
from agentic.problem.coder.planner import make_planner
from agentic.problem.coder.worker import make_worker
from agentic.problem.coder.critic import make_critic


def make_agent_dispatcher(
    client: OpenAI,
    model: str = "gpt-4.1-mini",
    max_retries: int = 3,
) -> CoderDispatcher:
    planner = make_planner(client, model=model)
    worker = make_worker(client, model=model)
    critic = make_critic(client, model=model)
    return CoderDispatcher(
        max_retries=max_retries,
        planner=planner,
        workers={"coder-worker": worker},
        critic=critic,
    )


def make_tool_registry() -> ToolRegistry:
    # Coding domain has no external tools; return an empty registry for parity.
    return ToolRegistry()
