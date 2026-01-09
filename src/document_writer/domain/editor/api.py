"""Editor transform contract for a single text chunk.

The editor accepts one text chunk and an opaque, plain-text policy. Identity is valid.
No global context, cross-chunk awareness, or structural changes are assumed or required.
"""

from typing import Any, Self

from pydantic import BaseModel, ConfigDict, model_validator


class AgentEditorRequest(BaseModel):
    """Single-chunk edit request (text_chunk + policy_text + advisory intent).

    Contract notes:
    - document maps to text_chunk (single, standalone input chunk).
    - editing_policy maps to policy_text (plain text only; no structure or parsing).
    - intent is advisory only.
    - Identity output is valid.
    - The editor must not change structure, reorder content, or alter tone unless policy demands it.
    """

    model_config = ConfigDict(extra="forbid")

    document: str
    editing_policy: str
    intent: Any | None = None

    @model_validator(mode="after")
    def validate_required_text(self) -> Self:
        if not self.document or not self.document.strip():
            raise ValueError("document must be a non-empty string")
        if not self.editing_policy or not self.editing_policy.strip():
            raise ValueError("editing_policy must be a non-empty string")
        return self


class AgentEditorResponse(BaseModel):
    """Single-chunk edit response containing the edited text chunk (identity allowed)."""

    model_config = ConfigDict(frozen=True)

    edited_document: str
    trace: list[dict] | None = None

    @model_validator(mode="after")
    def validate_edited_document(self) -> Self:
        if not self.edited_document or not self.edited_document.strip():
            raise ValueError("edited_document must be a non-empty string")
        return self
