from typing import Any

from pydantic import BaseModel

from domain.document.types import DocumentTree, DocumentTask


class DocumentPlannerInput(BaseModel):
    document_tree: DocumentTree | None = None
    tone: str | None = None
    audience: str | None = None
    goal: str | None = None


class DocumentPlannerOutput(BaseModel):
    task: DocumentTask
