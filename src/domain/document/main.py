import argparse
from dotenv import load_dotenv
from openai import OpenAI

from agentic.analysis_supervisor import (
    AnalysisSupervisorRequest,
    run_analysis_supervisor,
)
from domain.document.planner import make_planner
from domain.document.schemas import DocumentPlannerInput
from domain.document.types import DocumentState
from agentic.agent_dispatcher import AgentDispatcher
from agentic.logging_config import get_logger

logger = get_logger("domain.document.main")


def _pretty_print_run(run: dict, trace: bool = False) -> None:
    """Render the analysis supervisor output in a readable diagnostic summary."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    print("Document analysis supervisor run complete:")
    print(f"  Task: {_serialize(run.task)}")
    print(f"  Plan: {_serialize(run.plan)}")
    if trace and run.trace:
        print("  Trace:")
        for entry in run.trace:
            print(f"    {_serialize(entry)}")


def main() -> None:
    load_dotenv(override=True)

    parser = argparse.ArgumentParser(
        description="Run the document analysis supervisor (planner-only)."
    )
    parser.add_argument(
        "--tone",
        type=str,
        default=None,
        help="Optional document tone (e.g. formal, academic).",
    )
    parser.add_argument(
        "--audience",
        type=str,
        default=None,
        help="Optional target audience.",
    )
    parser.add_argument(
        "--goal",
        type=str,
        default=None,
        help="Optional document goal.",
    )
    args = parser.parse_args()

    client = OpenAI()

    # --- Planner-only dispatcher ---
    planner = make_planner(client, model="gpt-4.1-mini")
    dispatcher = AgentDispatcher(
        planner=planner,
        workers={},      # REQUIRED: empty, analysis-only
        critic=None,     # type: ignore[arg-type]
    )

    # --- Initial document state ---
    # For now, start with no state (first planning step).
    document_state: DocumentState | None = None

    planner_input = DocumentPlannerInput(
        document_state=document_state,
        tone=args.tone,
        audience=args.audience,
        goal=args.goal,
    )

    supervisor_input = AnalysisSupervisorRequest(
        task=planner_input
    )

    run = run_analysis_supervisor(
        supervisor_input,
        dispatcher=dispatcher,
    )

    _pretty_print_run(run)


if __name__ == "__main__":
    main()
