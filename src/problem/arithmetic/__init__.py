from .types import (
    Task,
    Result,
    ArithmeticPlannerInput,
    ArithmeticPlannerOutput,
    ArithmeticWorkerInput,
    ArithmeticWorkerOutput,
    ArithmeticCriticInput,
    ArithmeticCriticOutput,
    ArithmeticDispatcher,
)
from .planner import make_planner
from .worker import make_worker
from .critic import make_critic
from .tools import make_tool_registry


def make_agent_dispatcher(client, model: str = "gpt-4.1-mini", max_retries: int = 3) -> ArithmeticDispatcher:
    planner = make_planner(client, model=model)
    worker = make_worker(client, model=model)
    critic = make_critic(client, model=model)
    return ArithmeticDispatcher(
        max_retries=max_retries,
        planner=planner,
        worker=worker,
        critic=critic,
    )

__all__ = [
    "Task",
    "Result",
    "ArithmeticPlannerInput",
    "ArithmeticPlannerOutput",
    "ArithmeticWorkerInput",
    "ArithmeticWorkerOutput",
    "ArithmeticCriticInput",
    "ArithmeticCriticOutput",
    "ArithmeticDispatcher",
    "make_agent_dispatcher",
    "make_planner",
    "make_worker",
    "make_critic",
    "make_tool_registry",
]
