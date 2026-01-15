from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator
from document_writer.domain.intent.types import IntentEnvelope

class DocumentGenerateRequest(BaseModel):
    intent: IntentEnvelope


class DocumentSaveRequest(BaseModel):
    markdown: str
    filename: str | None = Field(default=None, description="Optional filename for the markdown download.")


class TitleSuggestRequest(BaseModel):
    content: str


class TitleSetRequest(BaseModel):
    post_id: str
    title: str


class EditContentRequest(BaseModel):
    post_id: str
    content: str


class BlogEditScope(BaseModel):
    mode: Literal["all", "chunks"]
    chunk_indices: list[int] | None = None


class BlogEditRequest(BaseModel):
    """
    v2 edit contract. Hard rules:
    - Only draft posts allowed.
    - Title must not change.
    - No publish side effects.
    - No regeneration.
    - Editor output is authoritative only after validation.
    """
    post_id: str
    policy_text: str | None = None
    policy_id: str | None = None
    scope: BlogEditScope | None = None

    @model_validator(mode="after")
    def validate_policy(self) -> Self:
        has_text = bool(self.policy_text and self.policy_text.strip())
        has_id = bool(self.policy_id and self.policy_id.strip())
        if has_text == has_id:
            raise ValueError("Exactly one of policy_text or policy_id must be provided.")
        return self


class BlogEditRejectedChunk(BaseModel):
    chunk_index: int
    reason: str


class BlogEditResponse(BaseModel):
    """
    v2 edit contract response. Hard rules:
    - Only draft posts allowed.
    - Title must not change.
    - No publish side effects.
    - No regeneration.
    - Editor output is authoritative only after validation.
    """
    post_id: str
    revision_id: int
    changed_chunks: list[int]
    rejected_chunks: list[BlogEditRejectedChunk]
    content: str
