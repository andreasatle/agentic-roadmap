from typing import Any

from pydantic import BaseModel

from domain.document.types import DocumentTree, DocumentTask
from domain.intent.types import IntentEnvelope


class DocumentPlannerInput(BaseModel):
    """Planner input; intent is advisory and read-only. Planner retains structural authority."""
    document_tree: DocumentTree | None = None
    tone: str | None = None
    audience: str | None = None
    goal: str | None = None
    intent: IntentEnvelope | None = None


class DocumentPlannerOutput(BaseModel):
    document_tree: DocumentTree
