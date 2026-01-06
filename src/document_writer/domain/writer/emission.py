from document_writer.domain.document.types import DocumentTree, DocumentNode
from document_writer.domain.document.content import ContentStore
from document_writer.domain.writer.types import DraftSectionTask, RefineSectionTask, WriterTask
from document_writer.domain.writer.intent_projection import apply_advisory_intent
from document_writer.domain.intent.types import IntentEnvelope


def emit_writer_tasks(
    tree: DocumentTree,
    store: ContentStore,
    intent: IntentEnvelope | None = None,
    applies_thesis_rule: bool = False,
) -> list[WriterTask]:
    tasks: list[WriterTask] = []

    def visit(node: DocumentNode) -> None:
        has_content = node.id in store.by_node_id
        task: WriterTask
        if has_content:
            task = RefineSectionTask(
                node_id=node.id,
                section_name=node.title,
                purpose=node.description,
                requirements=[node.description],
                applies_thesis_rule=applies_thesis_rule,
            )
        else:
            task = DraftSectionTask(
                node_id=node.id,
                section_name=node.title,
                purpose=node.description,
                requirements=[node.description],
                applies_thesis_rule=applies_thesis_rule,
            )
        tasks.append(task)
        for child in node.children:
            visit(child)

    for child in tree.root.children:
        visit(child)
    return [apply_advisory_intent(task, intent) for task in tasks]
