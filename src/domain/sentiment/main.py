from __future__ import annotations

import argparse
from dotenv import load_dotenv
from openai import OpenAI

from domain.sentiment import make_agent_dispatcher, make_tool_registry, problem_state_cls
from agentic.supervisor import Supervisor
from domain.sentiment.factory import SentimentContentState


def _pretty_print_run(run: dict) -> None:
    """Render the supervisor output in a readable diagnostic summary."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    plan = run.plan
    result = run.result
    decision = run.decision
    loops_used = run.loops_used

    print("Sentiment supervisor run complete:")
    print(f"  Plan: {_serialize(plan)}")
    print(f"  Result: {_serialize(result)}")
    print(f"  Decision: {_serialize(decision)}")
    print(f"  Loops used: {loops_used}")


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Run the sentiment supervisor.")
    parser.parse_args()
    client = OpenAI()

    tool_registry = make_tool_registry()
    dispatcher = make_agent_dispatcher(client, model="gpt-4.1-mini", max_retries=3)
    state = SentimentContentState()

    supervisor = Supervisor(
        dispatcher=dispatcher,
        tool_registry=tool_registry,
        domain_state=state,
        max_loops=5,
        problem_state_cls=problem_state_cls,
    )
    run = supervisor()
    _pretty_print_run(run)


if __name__ == "__main__":
    main()
