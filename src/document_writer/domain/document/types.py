from typing import Any, Literal
from pydantic import BaseModel, Field, model_validator


class DocumentTask(BaseModel):
    op: Literal["init", "split", "merge", "reorder", "delete", "emit_writer_tasks"]
    target: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_semantics(self) -> "DocumentTask":
        match self.op:
            case "init":
                if self.target is not None:
                    raise ValueError("init requires target=None")
                if "root" not in self.parameters:
                    raise ValueError("init requires parameters.root")
                if not isinstance(self.parameters.get("root"), DocumentNode):
                    raise ValueError("init requires parameters.root to be a DocumentNode")
            case "split":
                if not self.target:
                    raise ValueError("split requires target node id")
                children = self.parameters.get("children")
                if children is None:
                    raise ValueError("split requires parameters.children")
                if not isinstance(children, list) or not all(isinstance(c, DocumentNode) for c in children):
                    raise ValueError("split requires parameters.children to be a list[DocumentNode]")
            case "merge":
                source_ids = self.parameters.get("source_ids")
                new_node = self.parameters.get("new_node")
                if not source_ids or not isinstance(source_ids, list) or not all(isinstance(s, str) for s in source_ids):
                    raise ValueError("merge requires parameters.source_ids as list[str]")
                if not isinstance(new_node, DocumentNode):
                    raise ValueError("merge requires parameters.new_node as DocumentNode")
            case "reorder":
                parent_id = self.parameters.get("parent_id")
                ordered_child_ids = self.parameters.get("ordered_child_ids")
                if not parent_id or not isinstance(parent_id, str):
                    raise ValueError("reorder requires parameters.parent_id")
                if (
                    not ordered_child_ids
                    or not isinstance(ordered_child_ids, list)
                    or not all(isinstance(cid, str) for cid in ordered_child_ids)
                ):
                    raise ValueError("reorder requires parameters.ordered_child_ids as list[str]")
            case "delete":
                if not self.target:
                    raise ValueError("delete requires target node id")
                if self.parameters:
                    raise ValueError("delete requires empty parameters")
            case "emit_writer_tasks":
                pass
            case _:
                raise ValueError(f"Unsupported op: {self.op}")
        return self


class DocumentNode(BaseModel):
    """Immutable structural node for the document outline.

    Guarantees:
    - Structure ownership lives in the Document layer; Writer receives these nodes as read-only context.
    - id is opaque, unique within a tree, and stable for the duration of a writer run.
    - title is a human-readable label; description is the semantic obligation the Writer must satisfy.
    """

    id: str
    title: str
    description: str
    children: list["DocumentNode"] = Field(default_factory=list)


class DocumentTree(BaseModel):
    """Complete document structure provided by the Document layer.

    The tree is complete and immutable for a writer run; Writer consumes it but never mutates or enriches it.
    Content is intentionally absent; text binding lives externally via {DocumentNode.id → text}.
    """

    root: DocumentNode
