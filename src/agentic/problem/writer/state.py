from __future__ import annotations

from pydantic import BaseModel, Field

from agentic.problem.writer.types import WriterResult, WriterTask


class WriterState(BaseModel):
    sections: dict[str, str] = Field(default_factory=dict)

    def update(self, task: WriterTask, result: WriterResult) -> "WriterState":
        new_sections = dict(self.sections)
        new_sections[task.section_name] = result.text
        return WriterState(sections=new_sections)


class ProblemState(BaseModel):
    """
    Domain-specific persistent state.
    MUST NOT mutate in-place; always return a new instance from update().
    """

    content: str = ""

    def update(self, task: WriterTask, result: WriterResult) -> ProblemState:
        """
        Return a NEW ProblemState instance updated with accepted worker result.
        Default behavior: no change.
        """
        return self
