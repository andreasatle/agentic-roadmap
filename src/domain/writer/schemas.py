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
from domain.writer.state import WriterState


class WriterDomainState(BaseModel):
    draft_text: str | None = None
    refinement_steps: int = 0
    completed_sections: list[str] | None = None

    def update(self, task, result):
        completed = list(self.completed_sections or [])
        name = getattr(task, "section_name", None)
        if name and name not in completed:
            completed.append(name)
        return WriterDomainState(
            draft_text=getattr(result, "text", self.draft_text),
            refinement_steps=self.refinement_steps,
            completed_sections=completed or None,
        )

    def snapshot_for_llm(self) -> dict:
        return self.model_dump(exclude_none=True)

class WriterPlannerInput(PlannerInput[WriterTask, WriterResult]):
    """Supervisor context for the writer planner."""

    model_config = ConfigDict(extra="allow")

    topic: str | None = None
    project_state: WriterState | None = None


class WriterPlannerOutput(PlannerOutput[WriterTask]):
    """Planner response carrying the next writer task and worker routing."""

    model_config = ConfigDict(populate_by_name=True)

    task: WriterTask = Field(..., alias="next_task")
    worker_id: str = "writer-worker"


class WriterWorkerInput(WorkerInput[WriterTask, WriterResult]):
    """Work request for the writer worker."""

    model_config = ConfigDict(populate_by_name=True)

    previous_text: str | None = None
    writer_state: WriterState | None = None

    @model_validator(mode="after")
    def sync_previous_fields(self) -> "WriterWorkerInput":
        """
        Keep previous_text and previous_result aligned so supervisors relying on
        previous_result remain compatible.
        """
        if self.previous_text and self.previous_result is None:
            self.previous_result = WriterResult(text=self.previous_text)

        if self.previous_result is not None and self.previous_text is None:
            match self.previous_result:
                case WriterResult():
                    self.previous_text = self.previous_result.text
                case _:
                    self.previous_text = str(self.previous_result)
        return self


WriterWorkerOutput = WorkerOutput[WriterResult]


class WriterCriticInput(CriticInput[WriterTask, WriterResult]):
    """Critic sees the planned task and the worker's text."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    plan: WriterTask = Field(..., alias="task")
    worker_answer: WriterResult = Field(..., alias="candidate")


class WriterCriticOutput(Decision):
    """Decision with a boolean convenience flag."""

    accepted: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def derive_decision_from_bool(cls, values: dict) -> dict:
        match values:
            case dict():
                if "accepted" in values and "decision" not in values:
                    values = dict(values)
                    accepted = values.get("accepted")
                    if accepted is not None:
                        values["decision"] = "ACCEPT" if accepted else "REJECT"
        return values

    @model_validator(mode="after")
    def backfill_accepted(self) -> "WriterCriticOutput":
        self.accepted = self.decision == "ACCEPT"
        return self
