from pydantic import ConfigDict, Field, model_validator
from pathlib import Path
import json
import re

from agentic.common.load_save_mixin import LoadSaveMixin
from agentic.schemas import (
    CriticInput,
    Decision,
    PlannerInput,
    PlannerOutput,
    WorkerInput,
    WorkerOutput,
)

from domain.writer.types import WriterResult, WriterTask
from domain.writer.state import WriterContentState


class WriterDomainState(LoadSaveMixin):
    draft_text: str | None = None
    refinement_steps: int = 0
    completed_sections: list[str] | None = None
    topic: str | None = None
    content: WriterContentState = Field(default_factory=WriterContentState)

    @classmethod
    def topic_key(cls, topic: str | None) -> str:
        if topic is None or not str(topic).strip():
            return "default"
        slug = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(topic).strip().lower()).strip("-")
        return slug or "default"

    @classmethod
    def load(cls, topic: str | None = None) -> "WriterDomainState":
        key = cls.topic_key(topic)
        base = Path(".agentic_state") / "writer"
        path = base / f"{key}.json"
        if not path.exists():
            return cls(topic=topic)
        data = json.loads(path.read_text())
        return cls.model_validate({**data, "topic": topic})

    def save(self, topic: str | None = None) -> None:
        effective_topic = topic if topic is not None else self.topic
        key = self.topic_key(effective_topic)
        base = Path(".agentic_state") / "writer"
        base.mkdir(parents=True, exist_ok=True)
        path = base / f"{key}.json"
        path.write_text(self.model_dump_json(indent=2))

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
            topic=self.topic,
            content=new_content,
        )

    def snapshot_for_llm(self) -> dict:
        data = {}
        if self.refinement_steps:
            data["refinement_steps"] = self.refinement_steps
        if self.completed_sections:
            data["completed_sections"] = self.completed_sections
        if self.content.section_order:
            data["section_order"] = self.content.section_order
        return data

class WriterPlannerInput(PlannerInput[WriterTask, WriterResult]):
    """Supervisor context for the writer planner."""

    model_config = ConfigDict(extra="allow")

    project_state: dict | None = None
    topic: str | None = None
    tone: str | None = None
    audience: str | None = None
    length: str | None = None


class WriterPlannerOutput(PlannerOutput[WriterTask]):
    """Planner response carrying the next writer task and worker routing."""

    model_config = ConfigDict(populate_by_name=True)

    task: WriterTask
    worker_id: str = "writer-worker"
    section_order: list[str] | None = None


class WriterWorkerInput(WorkerInput[WriterTask, WriterResult]):
    """Work request for the writer worker."""

    model_config = ConfigDict(populate_by_name=True)

    writer_state: WriterContentState | None = None


WriterWorkerOutput = WorkerOutput[WriterResult]


class WriterCriticInput(CriticInput[WriterTask, WriterResult]):
    """Critic sees the planned task and the worker's text."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    plan: WriterTask = Field(..., alias="task")
    worker_answer: WriterResult = Field(..., alias="candidate")


class WriterCriticOutput(Decision):
    """Decision with a boolean convenience flag."""

    accepted: bool | None = None

    @model_validator(mode="after")
    def backfill_accepted(self) -> "WriterCriticOutput":
        self.accepted = self.decision == "ACCEPT"
        return self
