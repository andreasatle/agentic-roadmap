from openai import OpenAI

from agentic.tool_registry import ToolRegistry
from domain.coder.types import CoderDispatcher
from domain.coder.planner import make_planner
from domain.coder.worker import make_worker
from domain.coder.critic import make_critic


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
