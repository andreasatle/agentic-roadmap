from __future__ import annotations

from uuid import uuid4

from dotenv import load_dotenv
from openai import OpenAI

from domain.arithmetic import (
    ArithmeticPlannerInput,
    make_agent_dispatcher,
    make_tool_registry,
    problem_state_cls,
)
from agentic.supervisor import Supervisor


def _pretty_print_run(run: dict) -> None:
    """Render the supervisor output in a readable diagnostic summary."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    plan = run.get("plan")
    result = run.get("result")
    decision = run.get("decision")
    loops_used = run.get("loops_used")

    print("Arithmetic supervisor run complete:")
    print(f"  Plan: {_serialize(plan)}")
    print(f"  Result: {_serialize(result)}")
    print(f"  Decision: {_serialize(decision)}")
    print(f"  Loops used: {loops_used}")


def main() -> None:
    load_dotenv(override=True)
    client = OpenAI()

    initial_planner_input = ArithmeticPlannerInput(random_seed=str(uuid4()))
    tool_registry = make_tool_registry()
    dispatcher = make_agent_dispatcher(client, model="gpt-4.1-mini", max_retries=3)

    supervisor = Supervisor(
        dispatcher=dispatcher,
        tool_registry=tool_registry,
        max_loops=5,
        planner_defaults=initial_planner_input.model_dump(),
        problem_state_cls=problem_state_cls,
    )
    run = supervisor()
    _pretty_print_run(run)


if __name__ == "__main__":
    main()
