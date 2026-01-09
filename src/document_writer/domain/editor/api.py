from typing import Any, Self

from pydantic import BaseModel, ConfigDict, model_validator


class AgentEditorRequest(BaseModel):
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
    model_config = ConfigDict(frozen=True)

    edited_document: str
    trace: list[dict] | None = None

    @model_validator(mode="after")
    def validate_edited_document(self) -> Self:
        if not self.edited_document or not self.edited_document.strip():
            raise ValueError("edited_document must be a non-empty string")
        return self
