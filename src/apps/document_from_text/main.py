import argparse
from pathlib import Path
from dotenv import load_dotenv

from domain.intent import make_text_intent_controller
from domain.intent.text_prompt_refiner import make_text_prompt_refiner_controller
from domain.document.planner import make_planner
from domain.document.api import analyze
from domain.document.content import ContentStore
from domain.document.types import DocumentTree, DocumentNode
from domain.writer import make_agent_dispatcher as make_writer_dispatcher, make_tool_registry as make_writer_tool_registry
from domain.writer.api import execute_document
from agentic.agent_dispatcher import AgentDispatcher
from agentic.logging_config import get_logger
from domain.document.schemas import DocumentPlannerOutput

logger = get_logger("apps.document_from_text")


def _read_text(text: str | None, path: str | None) -> str:
    if text and path:
        raise ValueError("Provide exactly one of --text or --text-path, not both.")
    if text:
        return text
    if path:
        return Path(path).read_text()
    raise ValueError("Either --text or --text-path is required.")


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


def main() -> None:
    load_dotenv(override=True)
    parser = argparse.ArgumentParser(description="Run text → intent adapter into document writer.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--text",
        type=str,
        default=None,
        help="Inline raw user text.",
    )
    group.add_argument(
        "--text-path",
        type=str,
        default=None,
        help="Path to raw user text file.",
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
        help="Print advisory intent observation and audit.",
    )
    args = parser.parse_args()

    raw_text = _read_text(args.text, args.text_path)
    refiner = make_text_prompt_refiner_controller(model="gpt-4.1-mini")
    refined_text = refiner(raw_text)
    intent_controller = make_text_intent_controller(model="gpt-4.1-mini")
    intent = intent_controller(refined_text)

    # Document analysis
    planner = make_planner(model="gpt-4.1-mini")
    dispatcher = AgentDispatcher(
        planner=planner,
        workers={},
        critic=None,  # type: ignore[arg-type]
    )
    analysis = analyze(
        document_tree=None,
        tone=None,
        audience=None,
        goal=None,
        intent=intent,
        dispatcher=dispatcher,
    )
    if args.trace:
        print("Advisory: document intent observation =", getattr(analysis, "intent_observation", None))
    planned_tree: DocumentTree = DocumentPlannerOutput.model_validate(analysis.plan).document_tree

    # Writer execution
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
    if args.trace:
        print("Advisory: writer intent audit =", writer_result.intent_audit.model_dump())

    markdown_lines = assemble_markdown(planned_tree.root, writer_result.content_store)
    output_text = "\n\n".join(markdown_lines)

    out_path = Path(args.out) if args.out else None
    if out_path:
        out_path.write_text(output_text)
        print(f"Wrote assembled document to {out_path}")
    else:
        print("\nAssembled Document:\n")
        print(output_text)


if __name__ == "__main__":
    main()
