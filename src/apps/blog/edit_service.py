from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict

from agentic_framework.agent_dispatcher import AgentDispatcherBase
from document_writer.domain.editor import edit_document, make_editor_agent, AgentEditorRequest
from document_writer.domain.editor.chunking import Chunk, split_markdown, join_chunks

from apps.blog.storage import read_post_content, read_post_intent, read_post_meta
from apps.blog.post_revision_writer import PostRevisionWriter
from apps.blog.paths import POSTS_ROOT


class RejectedChunk(BaseModel):
    model_config = ConfigDict(extra="forbid")

    chunk_index: int
    reason: str


class EditResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    post_id: str
    revision_id: int
    changed_chunks: list[int]
    rejected_chunks: list[RejectedChunk]
    content: str


def _hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def apply_policy_edit(
    post_id: str,
    policy_text: str,
    *,
    actor_id: str | None = None,
) -> EditResult:
    post_dir = POSTS_ROOT / post_id
    if not post_dir.exists():
        raise FileNotFoundError(f"Post not found: {post_dir}")

    content_path = post_dir / "content.md"
    meta = read_post_meta(post_id)
    if meta.status != "draft":
        raise RuntimeError(f"Cannot edit non-draft post: {post_id}")

    document = read_post_content(post_id)
    before_hash = _hash_text(document)
    intent = read_post_intent(post_id)
    policy_hash = hashlib.sha256(policy_text.encode("utf-8")).hexdigest()

    agent = make_editor_agent()
    dispatcher = AgentDispatcherBase()
    writer = PostRevisionWriter()
    # Policy edits are clients of the canonical revision mechanism.

    chunks = split_markdown(document)
    original_chunks = chunks
    changed_indices: list[int] = []
    rejected_chunks: list[RejectedChunk] = []
    updated_chunks: list[Chunk] = []
    try:
        for chunk in chunks:
            response = edit_document(
                AgentEditorRequest(
                    document=chunk.text,
                    editing_policy=policy_text,
                    intent=intent,
                ),
                dispatcher=dispatcher,
                editor_agent=agent,
            )
            if response.edited_document != chunk.text:
                changed_indices.append(chunk.index)
                updated_chunks.append(
                    Chunk(
                        index=chunk.index,
                        text=response.edited_document,
                        leading_separator=chunk.leading_separator,
                        trailing_separator=chunk.trailing_separator,
                    )
                )
            else:
                updated_chunks.append(chunk)
    except ValueError as exc:
        writer.apply_delta(
            post_id,
            actor={"type": "policy", "id": actor_id or "policy"},
            delta_type="content_policy_edit",
            delta_payload={
                "changed_chunks": [],
                "before_hash": before_hash,
                "after_hash": before_hash,
                "policy_hash": policy_hash,
                "rejected_chunks": [],
            },
            new_content=document,
            reason=str(exc),
            status="rejected",
        )
        raise
    except Exception as exc:
        writer.apply_delta(
            post_id,
            actor={"type": "policy", "id": actor_id or "policy"},
            delta_type="content_policy_edit",
            delta_payload={
                "changed_chunks": [],
                "before_hash": before_hash,
                "after_hash": before_hash,
                "policy_hash": policy_hash,
                "rejected_chunks": [],
            },
            new_content=document,
            reason=str(exc),
            status="rejected",
        )
        raise

    if not changed_indices:
        return EditResult(
            post_id=post_id,
            revision_id=0,
            changed_chunks=[],
            rejected_chunks=rejected_chunks,
            content=document,
        )

    assert [c.index for c in updated_chunks] == list(range(len(updated_chunks)))
    updated_document = join_chunks(updated_chunks)
    after_hash = _hash_text(updated_document)
    revision_id = writer.apply_delta(
        post_id,
        actor={"type": "policy", "id": actor_id or "policy"},
        delta_type="content_policy_edit",
        delta_payload={
            "changed_chunks": changed_indices,
            "before_hash": before_hash,
            "after_hash": after_hash,
            "policy_hash": policy_hash,
            "rejected_chunks": [chunk.model_dump() for chunk in rejected_chunks],
        },
        new_content=updated_document,
    )
    if not isinstance(revision_id, int):
        raise ValueError("Revision id must be an int")
    content_path.write_text(updated_document)

    return EditResult(
        post_id=post_id,
        revision_id=revision_id,
        changed_chunks=changed_indices,
        rejected_chunks=rejected_chunks,
        content=updated_document,
    )
