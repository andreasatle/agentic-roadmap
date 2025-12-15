
import argparse
from dotenv import load_dotenv
from openai import OpenAI

from domain.sentiment import make_agent_dispatcher, make_tool_registry
from agentic.supervisor import SupervisorDomainInput, SupervisorRequest, run_supervisor
from domain.sentiment.types import SentimentTask


def _pretty_print_run(run: dict, trace: bool = False) -> None:
    """Render the supervisor output in a readable diagnostic summary."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    plan = run.task
    result = run.worker_output
    decision = run.critic_decision

    print("Sentiment supervisor run complete:")
    print(f"  Plan: {_serialize(plan)}")
    print(f"  Result: {_serialize(result)}")
    print(f"  Decision: {_serialize(decision)}")
    if trace and run.trace:
        print("  Trace:")
        for entry in run.trace:
            print(f"    {_serialize(entry)}")


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Run the sentiment supervisor.")
    parser.parse_args()
    client = OpenAI()

    tool_registry = make_tool_registry()
    dispatcher = make_agent_dispatcher(client, model="gpt-4.1-mini", max_retries=3)
    task = SentimentTask(text="Test", target_sentiment="NEUTRAL")

    supervisor_input = SupervisorRequest(
        domain=SupervisorDomainInput(
            task=task,
        ),
    )
    run = run_supervisor(
        supervisor_input,
        dispatcher=dispatcher,
        tool_registry=tool_registry,
    )
    _pretty_print_run(run)


if __name__ == "__main__":
    main()
