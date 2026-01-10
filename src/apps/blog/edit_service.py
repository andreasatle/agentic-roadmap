from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict

from agentic_framework.agent_dispatcher import AgentDispatcherBase
from document_writer.domain.editor import edit_document, make_editor_agent, AgentEditorRequest
from document_writer.domain.editor.chunking import Chunk, split_markdown, join_chunks
from document_writer.domain.editor.validation import validate_diff

from apps.blog.storage import read_post_intent, read_post_meta


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


def apply_policy_edit(
    post_id: str,
    policy_text: str,
    posts_root: str = "posts",
) -> EditResult:
    post_dir = Path(posts_root) / post_id
    if not post_dir.exists():
        raise FileNotFoundError(f"Post not found: {post_dir}")

    content_path = post_dir / "content.md"
    meta_path = post_dir / "meta.yaml"
    meta = read_post_meta(post_id, posts_root)
    if meta.status != "draft":
        raise RuntimeError(f"Cannot edit non-draft post: {post_id}")

    document = content_path.read_text()
    intent = read_post_intent(post_id, posts_root)

    agent = make_editor_agent()
    dispatcher = AgentDispatcherBase()

    chunks = split_markdown(document)
    original_chunks = chunks
    changed_indices: list[int] = []
    rejected_chunks: list[RejectedChunk] = []
    updated_chunks: list[Chunk] = []
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
        validation = validate_diff(
            before=chunk.text,
            after=response.edited_document,
            policy_text=policy_text,
        )
        if not validation.accepted:
            rejected_chunks.append(
                RejectedChunk(chunk_index=chunk.index, reason=validation.reason)
            )
        if validation.accepted and response.edited_document != chunk.text:
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

    if not changed_indices:
        return EditResult(
            post_id=post_id,
            revision_id=0,
            changed_chunks=[],
            rejected_chunks=rejected_chunks,
            content=document,
        )

    revisions_dir = post_dir / "revisions"
    revisions_dir.mkdir(exist_ok=True)
    revision_ids: list[int] = []
    for entry in revisions_dir.glob("*.md"):
        stem = entry.stem
        if "_" in stem:
            stem = stem.split("_", 1)[0]
        if stem.isdigit():
            revision_ids.append(int(stem))
    next_rev = max(revision_ids, default=0) + 1

    for chunk in original_chunks:
        if chunk.index in changed_indices:
            snapshot_path = revisions_dir / f"{next_rev}_{chunk.index}.md"
            snapshot_path.write_text(chunk.text)

    assert [c.index for c in updated_chunks] == list(range(len(updated_chunks)))
    updated_document = join_chunks(updated_chunks)
    content_path.write_text(updated_document)

    if meta_path.exists():
        meta_payload = yaml.safe_load(meta_path.read_text()) or {}
        if not isinstance(meta_payload, dict):
            raise ValueError(f"Invalid meta.yaml for post {post_id}")
    else:
        meta_payload = {}
    revisions = meta_payload.get("revisions")
    if not isinstance(revisions, list):
        revisions = []
    revisions.append(
        {
            "revision_id": next_rev,
            "policy": policy_text,
            "changed_chunks": changed_indices,
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        }
    )
    meta_payload["revisions"] = revisions
    meta_path.write_text(yaml.safe_dump(meta_payload, sort_keys=False, default_flow_style=False))

    return EditResult(
        post_id=post_id,
        revision_id=next_rev,
        changed_chunks=changed_indices,
        rejected_chunks=rejected_chunks,
        content=updated_document,
    )
