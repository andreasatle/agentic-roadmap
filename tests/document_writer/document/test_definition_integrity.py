import pytest

from document_writer.domain.document.types import ConceptId, DocumentNode, DocumentTree
from document_writer.domain.document.validation import validate_definition_authority


def test_duplicate_definitions_fail():
    concept = ConceptId("alpha")
    node_a = DocumentNode(
        id="a",
        title="A",
        description="A",
        defines=[concept],
    )
    node_b = DocumentNode(
        id="b",
        title="B",
        description="B",
        defines=[concept],
    )
    root = DocumentNode(
        id="root",
        title="Root",
        description="Root",
        children=[node_a, node_b],
    )
    tree = DocumentTree(root=root)
    with pytest.raises(ValueError):
        validate_definition_authority(tree)


def test_missing_definition_fail():
    concept = ConceptId("beta")
    node_a = DocumentNode(
        id="a",
        title="A",
        description="A",
        assumes=[concept],
    )
    root = DocumentNode(
        id="root",
        title="Root",
        description="Root",
        children=[node_a],
    )
    tree = DocumentTree(root=root)
    with pytest.raises(ValueError):
        validate_definition_authority(tree)


def test_valid_tree_passes():
    concept = ConceptId("gamma")
    node_a = DocumentNode(
        id="a",
        title="A",
        description="A",
        defines=[concept],
    )
    node_b = DocumentNode(
        id="b",
        title="B",
        description="B",
        assumes=[concept],
    )
    root = DocumentNode(
        id="root",
        title="Root",
        description="Root",
        children=[node_a, node_b],
    )
    tree = DocumentTree(root=root)
    validate_definition_authority(tree)
