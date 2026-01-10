from pydantic import BaseModel, Field

from document_writer.domain.intent.types import IntentEnvelope


class IntentParseRequest(BaseModel):
    yaml_text: str = Field(..., description="Raw IntentEnvelope YAML text.")


class IntentSaveRequest(BaseModel):
    intent: IntentEnvelope
    filename: str | None = Field(default=None, description="Optional filename for the YAML download.")


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
