from typing import Any

from pydantic import BaseModel

from domain.document.types import DocumentState, DocumentTask


class DocumentPlannerInput(BaseModel):
    document_state: DocumentState | None = None
    tone: str | None = None
    audience: str | None = None
    goal: str | None = None


class DocumentPlannerOutput(BaseModel):
    task: DocumentTask
