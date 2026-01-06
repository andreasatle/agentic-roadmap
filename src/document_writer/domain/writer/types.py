
from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field


class BaseSectionTask(BaseModel):
    """Common structure for writer tasks.

    Invariants:
    - Exactly one task per DocumentNode; node_id links back to DocumentNode.id.
    - Writer tasks carry no structure; they reference nodes by id and use purpose/requirements only.
    - Writer has no authority to create, remove, or reorder sections.
    """

    model_config = ConfigDict(extra="forbid")

    node_id: str = Field(..., description="Opaque identifier for the section node.")
    section_name: str = Field(..., description="Human-readable label for the section.")
    purpose: str = Field(..., description="Brief intent for the section.")
    requirements: list[str] = Field(
        ..., description="Specific constraints or bullets the worker must satisfy."
    )
    forbidden_terms: list[str] = Field(
        default_factory=list,
        description="Terms that must NOT appear; advisory intent only.",
    )
    applies_thesis_rule: bool | None = Field(
        default=None,
        description="When true, this section participates in thesis enforcement.",
    )


class DraftSectionTask(BaseSectionTask):
    """Draft a new section for a single DocumentNode (identified by node_id)."""

    kind: Literal["draft_section"] = Field(
        "draft_section", description="Indicates this task drafts a section."
    )


class RefineSectionTask(BaseSectionTask):
    """Refine an existing section for a single DocumentNode (identified by node_id)."""

    kind: Literal["refine_section"] = Field(
        "refine_section", description="Indicates this task refines a section."
    )


WriterTask = Annotated[
    DraftSectionTask | RefineSectionTask, Field(discriminator="kind")
]
"""Union of writer tasks executed under bounded retry semantics; acceptance by the critic is terminal."""


class WriterResult(BaseModel):
    """Single section output keyed by one DocumentNode.id; no structural or persistence authority.

    - Bound to exactly one node via the surrounding task’s node_id.
    - Contains only section text; it does not imply storage, ordering, or assembly.
    - May be absent in non-convergent runs; when present and accepted, it is terminal for that attempt.
    """

    text: str = Field(..., description="Completed prose for the section.")
