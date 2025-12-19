from typing import Iterable

from pydantic import BaseModel, Field

from domain.document.types import DocumentTree
from domain.document.content import ContentStore
from domain.intent.types import IntentEnvelope


class IntentAuditResult(BaseModel):
    """Diagnostic-only report of intent satisfaction; has no authority over execution."""

    satisfied: bool
    missing_required_mentions: list[str] = Field(default_factory=list)
    violated_forbidden_terms: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _texts(store: ContentStore) -> Iterable[str]:
    return store.by_node_id.values()


def audit_intent_satisfaction(
    *,
    document_tree: DocumentTree,
    content_store: ContentStore,
    intent: IntentEnvelope | None,
) -> IntentAuditResult:
    """Best-effort, advisory-only audit of intent satisfaction. Does not affect execution."""
    if intent is None:
        return IntentAuditResult(
            satisfied=True,
            notes=["no intent provided"],
        )

    texts = [t.lower() for t in _texts(content_store)]
    missing: list[str] = []
    violated: list[str] = []
    notes: list[str] = []

    includes = list(intent.semantic_constraints.must_include) + list(
        intent.semantic_constraints.required_mentions
    )
    for item in includes:
        item_lower = item.lower()
        if not any(item_lower in text for text in texts):
            missing.append(item)

    for term in intent.semantic_constraints.must_avoid:
        term_lower = term.lower()
        if any(term_lower in text for text in texts):
            violated.append(term)

    satisfied = not missing and not violated
    if not texts:
        notes.append("no content to audit")

    return IntentAuditResult(
        satisfied=satisfied,
        missing_required_mentions=missing,
        violated_forbidden_terms=violated,
        notes=notes,
    )
