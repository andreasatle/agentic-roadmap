import argparse
from pathlib import Path
from dotenv import load_dotenv
from document_writer.domain.intent import load_intent_from_file
from agentic_workflow.logging_config import get_logger
from document_writer.apps.service import generate_document

logger = get_logger("document_writer.domain.document.main")


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
        description="Run document analysis followed by writer execution."
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
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Optional path to write assembled markdown output.",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="Optional advisory trace of intent observability and audit (no behavioral impact).",
    )
    args = parser.parse_args()
    intent = load_intent_from_file(args.intent) if args.intent else None
    out_path = Path(args.out) if args.out else None

    result = generate_document(
        intent=intent,
        trace=args.trace,
    )
    if args.trace and result.trace is not None:
        _pretty_print_run({"planner_input": None, "plan": None, "trace": result.trace}, trace=True)
        print("Advisory: writer intent audit =", getattr(result.intent_audit, "model_dump", lambda: result.intent_audit)())
    output_text = result.markdown

    if out_path:
        out_path.write_text(output_text)
        print(f"Wrote assembled document to {out_path}")
    else:
        print("\nAssembled Document:\n")
        print(output_text)


if __name__ == "__main__":
    main()
