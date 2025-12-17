from typing import Any, Literal
from pydantic import BaseModel, Field


class DocumentTask(BaseModel):
    op: Literal["init", "split", "merge", "reorder", "delete", "emit_writer_tasks"]
    target: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class DocumentNode(BaseModel):
    """Pure structural node describing the document outline."""

    id: str
    title: str
    description: str
    children: list["DocumentNode"] = Field(default_factory=list)


class DocumentState(BaseModel):
    sections: list[str]
