from openai import OpenAI

from agentic.tool_registry import ToolRegistry
from agentic.problem.arithmetic.types import (
    ArithmeticDispatcher,
    WORKER_CAPABILITIES,
    AddArgs,
    SubArgs,
    MulArgs,
)
from agentic.problem.arithmetic.planner import make_planner
from agentic.problem.arithmetic.worker import make_worker
from agentic.problem.arithmetic.critic import make_critic
from agentic.problem.arithmetic.tools import add, sub, mul
from agentic.common.state import StatelessProblemState

def make_agent_dispatcher(
    client: OpenAI,
    model: str = "gpt-4.1-mini",
    max_retries: int = 3,
) -> ArithmeticDispatcher:
    planner = make_planner(client, model=model)
    workers = {worker_id: make_worker(client, model=model, worker_id=worker_id) for worker_id in WORKER_CAPABILITIES}
    critic = make_critic(client, model=model)
    return ArithmeticDispatcher(
        max_retries=max_retries,
        planner=planner,
        workers=workers,
        critic=critic,
        domain_name="arithmetic",
    )


def make_tool_registry() -> ToolRegistry:
    tool_registry = ToolRegistry()
    tool_registry.register("add", "Deterministic addition tool.", add, AddArgs)
    tool_registry.register("sub", "Deterministic subtraction tool.", sub, SubArgs)
    tool_registry.register("mul", "Deterministic multiplication tool.", mul, MulArgs)
    return tool_registry

problem_state_cls = StatelessProblemState
