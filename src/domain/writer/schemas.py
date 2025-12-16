from typing import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentic.schemas import (
    CriticInput,
    Decision,
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
)

from domain.writer.types import WriterResult, WriterTask
from domain.writer.state import StructureState, WriterContentState


class WriterDomainState(BaseModel):
    draft_text: str | None = None
    refinement_steps: int = 0
    completed_sections: list[str] | None = None
    structure: StructureState = Field(default_factory=StructureState)
    content: WriterContentState = Field(default_factory=WriterContentState)

    def update(self, task, result, *, section_order: list[str] | None = None):
        completed = list(self.completed_sections or [])
        name = getattr(task, "section_name", None)
        if name and name not in completed:
            completed.append(name)
        new_content = self.content.update(task, result, section_order=section_order)
        return WriterDomainState(
            draft_text=getattr(result, "text", self.draft_text),
            refinement_steps=self.refinement_steps,
            completed_sections=completed or None,
            structure=self.structure,
            content=new_content,
        )

    def snapshot_for_llm(self) -> dict:
        data = {}
        if self.completed_sections:
            data["completed_sections"] = self.completed_sections
        if self.structure.sections:
            data["section_order"] = list(self.structure.sections)
        return data

class WriterPlannerInput(PlannerInput[WriterTask, WriterResult]):
    """Supervisor context for the writer planner."""

    model_config = ConfigDict(extra="allow")

    # instructions is preferred and opaque; other semantic fields are legacy and ignored by planner logic.
    project_state: WriterDomainState | None = None
    task: WriterTask
    instructions: str | None = None
    topic: str | None = None
    tone: str | None = None
    audience: str | None = None
    length: str | None = None


class WriterPlannerOutput(PlannerOutput[WriterTask]):
    """Planner response carrying the next writer task and worker routing."""

    model_config = ConfigDict(populate_by_name=True)

    task: WriterTask
    worker_id: str = Field(
        default="writer-draft-worker",
        description="Target worker identifier for execution.",
    )


class WriterWorkerInput(WorkerInput[WriterTask, WriterResult]):
    """Work request for the writer worker."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


WriterWorkerOutput = WorkerOutput[WriterResult]


class WriterCriticInput(CriticInput[WriterTask, WriterResult]):
    """Critic sees the planned task and the worker's text."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    plan: WriterTask
    worker_answer: WriterResult


class WriterCriticOutput(Decision):
    """Decision with a boolean convenience flag."""

    accepted: bool | None = None

    @model_validator(mode="after")
    def backfill_accepted(self) -> Self:
        self.accepted = self.decision == "ACCEPT"
        return self
