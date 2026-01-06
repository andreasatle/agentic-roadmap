from typing import Any

from pydantic import BaseModel

from document_writer.domain.document.types import DocumentTree
from document_writer.domain.intent.types import IntentEnvelope


class DocumentPlannerInput(BaseModel):
    """Planner input; intent is advisory and read-only. Planner retains structural authority."""
    intent: IntentEnvelope


class DocumentPlannerOutput(BaseModel):
    document_tree: DocumentTree
    applies_thesis_rule: bool | None = None
