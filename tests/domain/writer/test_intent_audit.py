from domain.document_writer.document.types import DocumentNode, DocumentTree
from domain.document_writer.document.content import ContentStore
from domain.document_writer.intent.types import IntentEnvelope, GlobalSemanticConstraints
from domain.writer.intent_audit import audit_intent_satisfaction


def _tree_with_single_child(text: str) -> tuple[DocumentTree, ContentStore]:
    child = DocumentNode(id="sec-1", title="Section", description="desc", children=[])
    root = DocumentNode(id="root", title="Root", description="root", children=[child])
    store = ContentStore(by_node_id={"sec-1": text})
    return DocumentTree(root=root), store


def test_intent_audit_satisfied():
    tree, store = _tree_with_single_child("Content includes alpha and beta throughout.")
    intent = IntentEnvelope(
        semantic_constraints=GlobalSemanticConstraints(
            must_include=["alpha"],
            must_avoid=["gamma"],
            required_mentions=["beta"],
        )
    )
    result = audit_intent_satisfaction(document_tree=tree, content_store=store, intent=intent)
    assert result.satisfied is True
    assert result.missing_required_mentions == []
    assert result.violated_forbidden_terms == []


def test_intent_audit_missing_required():
    tree, store = _tree_with_single_child("Content mentions alpha only.")
    intent = IntentEnvelope(
        semantic_constraints=GlobalSemanticConstraints(
            must_include=["alpha"],
            required_mentions=["delta"],
        )
    )
    result = audit_intent_satisfaction(document_tree=tree, content_store=store, intent=intent)
    assert result.satisfied is False
    assert "delta" in result.missing_required_mentions
