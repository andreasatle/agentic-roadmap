from __future__ import annotations

from pydantic import BaseModel, Field

from domain.writer.types import WriterResult, WriterTask


class WriterState(BaseModel):
    sections: dict[str, str] = Field(default_factory=dict)

    def update(self, task: WriterTask, result: WriterResult) -> "WriterState":
        return self

    def snapshot_for_llm(self) -> dict:
        """
        Return a small, JSON-serializable dictionary containing ONLY the state
        that the LLM should see. Expose section names only.
        """
        return {}


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

    def snapshot_for_llm(self) -> dict:
        """
        Return a small, JSON-serializable dictionary containing ONLY the state
        that the LLM should see. Default: expose nothing.
        """
        return {}
