from document_writer.domain.document.types import ConceptId, DocumentNode, DocumentTree


def validate_definition_authority(tree: DocumentTree) -> None:
    defined: dict[ConceptId, str] = {}
    assumed: list[tuple[ConceptId, str]] = []

    def _walk(node: DocumentNode) -> None:
        for concept_id in node.defines:
            if concept_id in defined:
                raise ValueError(
                    f"ConceptId defined more than once: {concept_id}"
                )
            defined[concept_id] = node.id
        for concept_id in node.assumes:
            assumed.append((concept_id, node.id))
        for child in node.children:
            _walk(child)

    _walk(tree.root)

    for concept_id, node_id in assumed:
        if concept_id not in defined:
            raise ValueError(
                f"ConceptId assumed without definition: {concept_id} (node {node_id})"
            )
