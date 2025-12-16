
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class BaseSectionTask(BaseModel):
    """Common structure for writer tasks."""

    model_config = ConfigDict(extra="forbid")

    section_name: str = Field(..., description="Human-readable label for the section.")
    purpose: str = Field(..., description="Brief intent for the section.")
    requirements: list[str] = Field(
        ..., description="Specific constraints or bullets the worker must satisfy."
    )


class DraftSectionTask(BaseSectionTask):
    """Draft a new section from instructions."""

    kind: Literal["draft_section"] = Field(
        "draft_section", description="Indicates this task drafts a section."
    )


class RefineSectionTask(BaseSectionTask):
    """Refine an existing section with new guidance."""

    kind: Literal["refine_section"] = Field(
        "refine_section", description="Indicates this task refines a section."
    )


WriterTask = Annotated[
    DraftSectionTask | RefineSectionTask, Field(discriminator="kind")
]


class WriterResult(BaseModel):
    """Text produced by the worker for a single writing task."""

    text: str = Field(..., description="Completed prose for the section.")
