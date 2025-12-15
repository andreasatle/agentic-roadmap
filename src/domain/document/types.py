from typing import Any, Literal
from pydantic import BaseModel, Field


class DocumentTask(BaseModel):
    op: Literal["init", "split", "merge", "reorder", "delete", "emit_writer_tasks"]
    target: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class DocumentState(BaseModel):
    sections: list[str]
