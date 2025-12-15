from __future__ import annotations

import argparse

from dotenv import load_dotenv
from openai import OpenAI

from domain.arithmetic import make_agent_dispatcher, make_tool_registry, problem_state_cls
from agentic.supervisor import (
    SupervisorControlInput,
    SupervisorDomainInput,
    SupervisorRequest,
    run_supervisor,
)
from domain.arithmetic.factory import ArithmeticContentState
from domain.arithmetic.types import ArithmeticTask


def _pretty_print_run(run: dict) -> None:
    """Render the supervisor output in a readable diagnostic summary."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    plan = run.plan
    result = run.result
    decision = run.decision
    loops_used = run.loops_used

    print("Arithmetic supervisor run complete:")
    print(f"  Plan: {_serialize(plan)}")
    print(f"  Result: {_serialize(result)}")
    print(f"  Decision: {_serialize(decision)}")
    print(f"  Loops used: {loops_used}")


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Run the arithmetic supervisor.")
    parser.parse_args()
    client = OpenAI()

    tool_registry = make_tool_registry()
    dispatcher = make_agent_dispatcher(client, model="gpt-4.1-mini", max_retries=3)
    state = ArithmeticContentState()
    task = ArithmeticTask(op="ADD", a=1, b=1)

    supervisor_input = SupervisorRequest(
        control=SupervisorControlInput(max_loops=5),
        domain=SupervisorDomainInput(
            domain_state=state,
            task=task,
        ),
    )
    run = run_supervisor(
        supervisor_input,
        dispatcher=dispatcher,
        tool_registry=tool_registry,
        problem_state_cls=problem_state_cls,
    )
    _pretty_print_run(run)


if __name__ == "__main__":
    main()
