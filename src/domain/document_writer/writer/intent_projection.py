from domain.document_writer.intent.types import IntentEnvelope
from domain.document_writer.writer.types import WriterTask


def apply_advisory_intent(task: WriterTask, intent: IntentEnvelope | None) -> WriterTask:
    """Advisory-only projection of intent onto writer task requirements. Idempotent and non-authoritative."""
    if intent is None:
        return task

    requirements = list(task.requirements)
    forbidden_terms = list(getattr(task, "forbidden_terms", []) or [])

    must_include = intent.semantic_constraints.must_include
    if must_include:
        req = f"Ensure the document includes: {', '.join(must_include)}"
        if req not in requirements:
            requirements.append(req)

    must_avoid = intent.semantic_constraints.must_avoid
    for term in must_avoid:
        if term not in forbidden_terms:
            forbidden_terms.append(term)

    return task.__class__(
        **{
            **task.model_dump(),
            "requirements": requirements,
            "forbidden_terms": forbidden_terms,
        }
    )
