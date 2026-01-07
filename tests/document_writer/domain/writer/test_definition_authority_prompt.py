from document_writer.domain.document.content import ContentStore
from document_writer.domain.document.types import ConceptId, DocumentNode, DocumentTree
from document_writer.domain.writer.emission import emit_writer_tasks
from document_writer.domain.writer.draft_worker import PROMPT_DRAFT_WORKER
from document_writer.domain.writer.refine_worker import PROMPT_REFINE_WORKER


def test_definition_authority_propagation_and_prompt_rules():
    defines = [ConceptId("alpha")]
    assumes = [ConceptId("beta")]
    node = DocumentNode(
        id="sec-1",
        title="Section",
        description="desc",
        defines=defines,
        assumes=assumes,
        children=[],
    )
    root = DocumentNode(
        id="root",
        title="Root",
        description="root",
        children=[node],
    )
    tree = DocumentTree(root=root)
    tasks = emit_writer_tasks(tree, ContentStore(), intent=None, applies_thesis_rule=False)

    assert len(tasks) == 1
    task = tasks[0]
    assert task.defines == defines
    assert task.assumes == assumes

    assert "Define ONLY the concepts listed in defines." in PROMPT_DRAFT_WORKER
    assert "DO NOT define any concepts listed in assumes." in PROMPT_DRAFT_WORKER
    assert "Define ONLY the concepts listed in defines." in PROMPT_REFINE_WORKER
    assert "DO NOT define any concepts listed in assumes." in PROMPT_REFINE_WORKER
