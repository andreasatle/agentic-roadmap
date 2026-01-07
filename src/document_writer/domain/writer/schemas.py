from typing import Self
from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentic_workflow.schemas import Decision, Feedback, PlannerOutput, WorkerOutput

from document_writer.domain.writer.types import DraftSectionTask, RefineSectionTask, WriterResult, WriterTask


class WriterPlannerInput(BaseModel):
    """Planner accepts only the concrete writer task."""

    model_config = ConfigDict(extra="forbid")

    task: WriterTask


class WriterPlannerOutput(PlannerOutput[WriterTask]):
    """Planner response carrying the next writer task and worker routing."""

    model_config = ConfigDict(populate_by_name=True)

    task: WriterTask
    worker_id: str = Field(
        default="writer-draft-worker",
        description="Target worker identifier for execution.",
    )


class DraftWorkerInput(BaseModel):
    """Work request for the draft worker."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    task: DraftSectionTask
    previous_result: WriterResult | None = None
    feedback: Feedback | None = None
    tool_result: WriterResult | None = None


class RefineWorkerInput(BaseModel):
    """Work request for the refine worker."""

    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    task: RefineSectionTask
    previous_result: WriterResult | None = None
    feedback: Feedback | None = None
    tool_result: WriterResult | None = None


WriterWorkerOutput = WorkerOutput[WriterResult]


class WriterCriticInput(BaseModel):
    """Critic sees the planned task and the worker's text."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    plan: WriterTask
    worker_answer: WriterResult
    node_description: str | None = None

    @model_validator(mode="after")
    def fill_node_description(self) -> Self:
        if self.node_description is None and hasattr(self.plan, "purpose"):
            self.node_description = getattr(self.plan, "purpose")
        return self


class WriterCriticOutput(Decision):
    """Decision with a boolean convenience flag."""

    accepted: bool | None = None

    @model_validator(mode="after")
    def backfill_accepted(self) -> Self:
        self.accepted = self.decision == "ACCEPT"
        return self
