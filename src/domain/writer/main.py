
import argparse
from dotenv import load_dotenv

from domain.writer import (
    make_agent_dispatcher,
    make_tool_registry,
)
from domain.writer.api import execute_document
from domain.document.types import DocumentTree, DocumentNode
from domain.document.content import ContentStore
from domain.document_writer.intent import load_intent_from_file


def _pretty_print_run(run: dict) -> None:
    """Render the single-task writer execution result."""
    def _serialize(value):
        return value.model_dump() if hasattr(value, "model_dump") else value

    plan = run.task
    result = run.worker_output
    decision = run.critic_decision

    print("Writer supervisor run complete:")
    print(f"  Plan: {_serialize(plan)}")
    print(f"  Result: {_serialize(result)}")
    print(f"  Decision: {_serialize(decision)}")
    if run.trace:
        print("  Trace:")
        for entry in run.trace:
            print(f"    {_serialize(entry)}")


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Run the writer supervisor.")
    parser.add_argument("--instructions", type=str, default="", help="Opaque task instructions.")
    parser.add_argument("--sections", type=str, default="", help="Comma-separated list of section names.")
    parser.add_argument(
        "--intent",
        type=str,
        default=None,
        help="Optional path to YAML intent envelope.",
    )
    args = parser.parse_args()
    intent = load_intent_from_file(args.intent) if args.intent else None

    instructions = args.instructions.strip()
    if not instructions:
        raise RuntimeError("Writer requires explicit instructions.")
    tool_registry = make_tool_registry()
    sections_arg = [s.strip() for s in args.sections.split(",") if s.strip()]
    if not sections_arg:
        raise RuntimeError(
            "Writer requires an explicit section name: no sections were provided."
        )

    children = [
        DocumentNode(
            id=section,
            title=section,
            description=f"Write the '{section}' section. Follow these global instructions: {instructions}",
            children=[],
        )
        for section in sections_arg
    ]
    document_tree = DocumentTree(
        root=DocumentNode(
            id="root",
            title="Document",
            description=instructions,
            children=children,
        )
    )
    content_store = ContentStore()
    dispatcher = make_agent_dispatcher(model="gpt-4.1-mini", max_retries=3)
    result = execute_document(
        document_tree=document_tree,
        content_store=content_store,
        dispatcher=dispatcher,
        tool_registry=tool_registry,
        intent=intent,
    )

    print("Writer execution complete. Sections written:")
    for node_id, text in result.content_store.by_node_id.items():
        print(f"- {node_id}: {text[:80]}")
    print("Intent audit (advisory):", result.intent_audit.model_dump())


if __name__ == "__main__":
    main()
