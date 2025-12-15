from __future__ import annotations

import argparse
from dotenv import load_dotenv
from openai import OpenAI

from domain.coder import make_agent_dispatcher, make_tool_registry
from agentic.supervisor import SupervisorDomainInput, SupervisorRequest, run_supervisor
from domain.coder.types import CodeTask

from agentic.logging_config import get_logger
logger = get_logger("domain.coder.main")

def _pretty_print_run(run: dict) -> None:
    """Render the supervisor output in a readable diagnostic summary."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    plan = run.task
    result = run.worker_output
    decision = run.critic_decision

    print("Coder supervisor run complete:")
    print(f"  Plan: {_serialize(plan)}")
    print(f"  Result: {_serialize(result)}")
    print(f"  Decision: {_serialize(decision)}")


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Run the coder supervisor.")
    parser.add_argument("--description", type=str, default="", help="Project description.")
    args = parser.parse_args()
    project_description = args.description.strip()
    if not project_description:
        raise SystemExit("A project description is required to start the coder supervisor.")
    # Supervisor now requires an explicit domain task; coder still relies on planner-generated tasks, so it is disabled until CoderTask is introduced.
    logger.warning(
        "Coder domain is disabled: it relies on planner-generated tasks. Introduce an explicit CoderTask before re-enabling."
    )
    return

    client = OpenAI()

    tool_registry = make_tool_registry()
    dispatcher = make_agent_dispatcher(client, model="gpt-4.1-mini", max_retries=3)
    state = ProblemState.load()
    task = CodeTask(language="python", specification=project_description, requirements=[project_description])

    supervisor_input = SupervisorRequest(
        domain=SupervisorDomainInput(
            domain_state=state,
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
