from domain.intent.types import IntentEnvelope
from domain.writer.types import WriterTask


def apply_advisory_intent(task: WriterTask, intent: IntentEnvelope | None) -> WriterTask:
    """Advisory-only projection of intent onto writer task requirements. Idempotent and non-authoritative."""
    if intent is None:
        return task

    requirements = list(task.requirements)

    must_include = intent.semantic_constraints.must_include
    if must_include:
        req = f"Ensure the document includes: {', '.join(must_include)}"
        if req not in requirements:
            requirements.append(req)

    must_avoid = intent.semantic_constraints.must_avoid
    if must_avoid:
        req = f"Avoid mentioning: {', '.join(must_avoid)}"
        if req not in requirements:
            requirements.append(req)

    return task.__class__(
        **{
            **task.model_dump(),
            "requirements": requirements,
        }
    )
