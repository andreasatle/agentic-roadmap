from __future__ import annotations

from typing import Literal
from pydantic import BaseModel, Field


class WriterTask(BaseModel):
    """Unit of writing work produced by the planner."""

    section_name: str = Field(..., description="Human-readable label for the section.")
    purpose: str = Field(..., description="Brief intent for the section.")
    operation: Literal["draft", "refine"]
    requirements: list[str] = Field(
        ..., description="Specific constraints or bullets the worker must satisfy."
    )


class WriterResult(BaseModel):
    """Text produced by the worker for a single writing task."""

    text: str = Field(..., description="Completed prose for the section.")


class WriterContextState(BaseModel):
    sections: dict[str, str] = Field(default_factory=dict)

    def update(self, task: WriterTask, result: WriterResult) -> WriterContextState:
        return self
