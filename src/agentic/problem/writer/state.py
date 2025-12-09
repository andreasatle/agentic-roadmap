from pydantic import BaseModel, Field


class WriterState(BaseModel):
    """
    Domain-specific state for the writer problem.
    Step 1: minimal structure only.
    This replaces untyped dict-based state in future steps.
    """
    accumulated_text: str = ""
    sections: list[str] = Field(default_factory=list)
    last_section_name: str | None = None
