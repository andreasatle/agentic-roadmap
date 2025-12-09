from pydantic import BaseModel, Field


class WriterTask(BaseModel):
    """Unit of writing work produced by the planner."""

    section_name: str = Field(..., description="Human-readable label for the section.")
    purpose: str = Field(..., description="Brief intent for the section.")
    requirements: list[str] = Field(
        ..., description="Specific constraints or bullets the worker must satisfy."
    )


class WriterResult(BaseModel):
    """Text produced by the worker for a single writing task."""

    text: str = Field(..., description="Completed prose for the section.")


class WriterState(BaseModel):
    """
    Domain-specific state for the writer problem.

    Step 1 MVP:
    - tracks completed sections
    - no behavior or validation yet
    """
    sections: dict[str, str] = Field(default_factory=dict)
