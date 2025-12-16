
import argparse

from dotenv import load_dotenv
from openai import OpenAI
#from anthropic import Anthropic

from domain.arithmetic import make_agent_dispatcher, make_tool_registry
from domain.arithmetic.types import ArithmeticTask
from domain.arithmetic.api import run


def _pretty_print_run(run: dict, trace: str = False) -> None:
    """Render the supervisor output in a readable diagnostic summary."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    plan = run.task
    result = run.worker_output
    decision = run.critic_decision

    print("Arithmetic supervisor run complete:")
    print(f"  Plan: {_serialize(plan)}")
    print(f"  Result: {_serialize(result)}")
    print(f"  Decision: {_serialize(decision)}")
    if trace and run.trace:
        print("  Trace:")
        for entry in run.trace:
            print(f"    {_serialize(entry)}")


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Run the arithmetic supervisor.")
    parser.parse_args()
    client = OpenAI()

    tool_registry = make_tool_registry()
    dispatcher = make_agent_dispatcher(client, model="gpt-5.2", max_retries=3)
    task = ArithmeticTask(op="ADD", a=1, b=1)

    result = run(
        task,
        dispatcher=dispatcher,
        tool_registry=tool_registry,
    )
    _pretty_print_run(result)


if __name__ == "__main__":
    main()
