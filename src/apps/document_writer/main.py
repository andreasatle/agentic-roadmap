import argparse
from pathlib import Path
from dotenv import load_dotenv
from domain.document.planner import make_planner
from domain.document.types import DocumentTree, DocumentNode
from domain.document.api import analyze
from domain.intent import load_intent_from_file
from domain.writer import make_agent_dispatcher as make_writer_dispatcher, make_tool_registry as make_writer_tool_registry
from domain.writer.api import execute_document
from domain.document.content import ContentStore
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
    parser.add_argument(
        "--out",
        type=str,
        default=None,
        help="Optional path to write assembled markdown output.",
    )
    args = parser.parse_args()
    intent = load_intent_from_file(args.intent) if args.intent else None
    out_path = Path(args.out) if args.out else None

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

    planned_tree: DocumentTree = run.plan.document_tree

    # Execute writer
    writer_dispatcher = make_writer_dispatcher(model="gpt-4.1-mini", max_retries=3)
    writer_tool_registry = make_writer_tool_registry()
    content_store = ContentStore()
    writer_result = execute_document(
        document_tree=planned_tree,
        content_store=content_store,
        dispatcher=writer_dispatcher,
        tool_registry=writer_tool_registry,
        intent=intent,
    )

    def assemble_markdown(node: DocumentNode, store: ContentStore, depth: int = 0) -> list[str]:
        lines: list[str] = []
        heading_prefix = "#" * (depth + 1)
        lines.append(f"{heading_prefix} {node.title}".strip())
        text = store.by_node_id.get(node.id)
        if text:
            lines.append(text.strip())
        for child in node.children:
            lines.extend(assemble_markdown(child, store, depth + 1))
        return lines

    markdown_lines = assemble_markdown(planned_tree.root, writer_result.content_store)
    output_text = "\n\n".join(markdown_lines)

    if out_path:
        out_path.write_text(output_text)
        print(f"Wrote assembled document to {out_path}")
    else:
        print("\nAssembled Document:\n")
        print(output_text)


if __name__ == "__main__":
    main()
