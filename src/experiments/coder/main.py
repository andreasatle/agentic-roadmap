
import argparse
from dotenv import load_dotenv

from experiments.coder import make_agent_dispatcher, make_tool_registry
from agentic_workflow.controller import ControllerDomainInput, ControllerRequest, run_controller
from experiments.coder.types import CodeTask

from agentic_workflow.logging_config import get_logger
logger = get_logger("experiments.coder.main")

def _pretty_print_run(run: dict, trace: bool = False) -> None:
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
    if trace and run.trace:
        print("  Trace:")
        for entry in run.trace:
            print(f"    {_serialize(entry)}")


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Run the coder supervisor.")
    parser.add_argument("--description", type=str, default="", help="Project description.")
    args = parser.parse_args()
    project_description = args.description.strip()
    if not project_description:
        raise SystemExit("A project description is required to start the coder supervisor.")
    # Controller now requires an explicit domain task; coder still relies on planner-generated tasks, so it is disabled until CoderTask is introduced.
    logger.warning(
        "Coder domain is disabled: it relies on planner-generated tasks. Introduce an explicit CoderTask before re-enabling."
    )
    return

if __name__ == "__main__":
    main()
