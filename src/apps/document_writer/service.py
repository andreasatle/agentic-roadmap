from dataclasses import dataclass
from typing import Any

from agentic.agent_dispatcher import AgentDispatcher
from domain.document.api import analyze
from domain.document.content import ContentStore
from domain.document.planner import make_planner
from domain.document.schemas import DocumentPlannerOutput
from domain.document.types import DocumentNode, DocumentTree
from domain.intent.types import IntentEnvelope
from domain.writer import make_agent_dispatcher as make_writer_dispatcher, make_tool_registry as make_writer_tool_registry
from domain.writer.api import execute_document


def _assemble_markdown(node: DocumentNode, store: ContentStore, depth: int = 0) -> list[str]:
    lines: list[str] = []
    heading_prefix = "#" * (depth + 1)
    text = store.by_node_id.get(node.id)
    text_to_emit = ""
    if text:
        text_lines = text.splitlines()
        filtered_lines: list[str] = []
        first_non_empty_seen = False
        for line in text_lines:
            if not first_non_empty_seen and line.strip():
                first_non_empty_seen = True
                if line == f"{node.title}:":
                    continue
            filtered_lines.append(line)
        text_to_emit = "\n".join(filtered_lines).strip()
    if text_to_emit:
        lines.append(f"{heading_prefix} {node.title}".strip())
        lines.append(text_to_emit)
    for child in node.children:
        lines.extend(_assemble_markdown(child, store, depth + 1))
    return lines


@dataclass
class DocumentGenerationResult:
    markdown: str
    document_tree: DocumentTree
    intent_audit: Any
    trace: list[dict] | None = None


def generate_document(
    *,
    goal: str | None,
    audience: str | None,
    tone: str | None,
    intent: IntentEnvelope | None,
    trace: bool = False,
) -> DocumentGenerationResult:
    # Planner-only dispatcher and analysis
    planner = make_planner(model="gpt-4.1-mini")
    dispatcher = AgentDispatcher(
        planner=planner,
        workers={},
        critic=None,  # type: ignore[arg-type]
    )
    analysis = analyze(
        document_tree=None,
        tone=tone,
        audience=audience,
        goal=goal,
        intent=intent,
        dispatcher=dispatcher,
    )

    planner_output = DocumentPlannerOutput.model_validate(analysis.plan)
    planned_tree: DocumentTree = planner_output.document_tree

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
        applies_thesis_rule=bool(planner_output.applies_thesis_rule),
    )

    markdown_lines = _assemble_markdown(planned_tree.root, writer_result.content_store)
    output_text = "\n\n".join(markdown_lines)

    return DocumentGenerationResult(
        markdown=output_text,
        document_tree=planned_tree,
        intent_audit=getattr(writer_result, "intent_audit", None),
        trace=analysis.trace if trace else None,
    )
