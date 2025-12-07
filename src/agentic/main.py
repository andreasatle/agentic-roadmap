from __future__ import annotations

from openai import OpenAI
from dotenv import load_dotenv
from agentic.supervisor import Supervisor
from agentic.logging_config import get_logger

from agentic.problem.arithmetic import make_agent_dispatcher, make_tool_registry
# from agentic.problem.sentiment import make_agent_dispatcher, make_tool_registry

load_dotenv(override=True)
logger = get_logger("agentic.main")


def run_demo(runs: int = 3) -> None:
    client = OpenAI()

    tool_registry = make_tool_registry()
    dispatcher = make_agent_dispatcher(client, model="gpt-4.1-mini", max_retries=3)

    supervisor = Supervisor(
        dispatcher=dispatcher,
        tool_registry=tool_registry,
        max_loops=5,
    )

    for i in range(1, runs + 1):
        response = supervisor()
        plan = response["plan"]
        result = response["result"]
        decision = response["decision"]
        loops_used = response["loops_used"]

        print(f"Run {i}:")
        print(f"  Plan: {plan.model_dump()}")
        print(f"  Result: {result.model_dump()}")
        print(f"  Decision: {decision.model_dump()}")
        print(f"  Loops used: {loops_used}")
        print("-" * 40)


if __name__ == "__main__":
    run_demo()
