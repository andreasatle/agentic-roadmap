from openai import OpenAI
from pydantic import BaseModel

from agentic.tool_registry import ToolRegistry
from agentic.problem.writer.dispatcher import WriterDispatcher
from agentic.problem.writer.planner import make_planner
from agentic.problem.writer.worker import make_worker
from agentic.problem.writer.critic import make_critic
from agentic.problem.writer.state import WriterState


def make_agent_dispatcher(
    client: OpenAI,
    model: str = "gpt-4.1-mini",
    max_retries: int = 3,
) -> WriterDispatcher:
    planner = make_planner(client, model=model)
    worker = make_worker(client, model=model)
    critic = make_critic(client, model=model)
    return WriterDispatcher(
        max_retries=max_retries,
        planner=planner,
        workers={"writer-worker": worker},
        critic=critic,
        domain_name="writer",
    )


def make_tool_registry() -> ToolRegistry:
    # Writer domain uses no tools in the MVP.
    return ToolRegistry()


def problem_state_cls() -> type[BaseModel]:
    return WriterState
