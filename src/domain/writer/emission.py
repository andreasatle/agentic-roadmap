from domain.document.types import DocumentTree, DocumentNode
from domain.document.content import ContentStore
from domain.writer.types import DraftSectionTask, RefineSectionTask, WriterTask
from domain.writer.intent_projection import apply_advisory_intent
from domain.intent.types import IntentEnvelope


def emit_writer_tasks(tree: DocumentTree, store: ContentStore, intent: IntentEnvelope | None = None) -> list[WriterTask]:
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
            )
        else:
            task = DraftSectionTask(
                node_id=node.id,
                section_name=node.title,
                purpose=node.description,
                requirements=[node.description],
            )
        tasks.append(task)
        for child in node.children:
            visit(child)

    for child in tree.root.children:
        visit(child)
    return [apply_advisory_intent(task, intent) for task in tasks]
