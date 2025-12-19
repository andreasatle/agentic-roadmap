import argparse
from dotenv import load_dotenv
from domain.document.planner import make_planner
from domain.document.types import DocumentTree
from domain.document.api import analyze
from domain.intent import load_intent_from_file
from agentic.agent_dispatcher import AgentDispatcher
from agentic.logging_config import get_logger

logger = get_logger("domain.document.main")


def _pretty_print_run(run: dict, trace: bool = False) -> None:
    """Render the analysis supervisor output in a readable diagnostic summary."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    print("Document analysis supervisor run complete:")
    print(f"  PlannerInput: {_serialize(run.planner_input)}")
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
    parser.add_argument(
        "--intent",
        type=str,
        default=None,
        help="Optional path to YAML intent envelope.",
    )
    args = parser.parse_args()
    intent = load_intent_from_file(args.intent) if args.intent else None

    # --- Planner-only dispatcher ---
    planner = make_planner(model="gpt-4.1-mini")
    dispatcher = AgentDispatcher(
        planner=planner,
        workers={},      # REQUIRED: empty, analysis-only
        critic=None,     # type: ignore[arg-type]
    )

    # --- Initial document state ---
    # For now, start with no tree (first planning step).
    document_tree: DocumentTree | None = None

    run = analyze(
        document_tree=document_tree,
        tone=args.tone,
        audience=args.audience,
        goal=args.goal,
        intent=intent,
        dispatcher=dispatcher,
    )

    _pretty_print_run(run)


if __name__ == "__main__":
    main()
