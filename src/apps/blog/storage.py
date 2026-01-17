from dataclasses import dataclass
from datetime import datetime, timezone
import copy
import hashlib
import os
import secrets
from pathlib import Path
from typing import Any, Literal

import yaml

from apps.blog.paths import POSTS_ROOT
from apps.blog.types import (
    BlogPostMeta,
    PostStatus,
    require_post_status,
    validate_status_transition,
)
from document_writer.domain.editor.chunking import Chunk, join_chunks, split_markdown


@dataclass
class RevisionResult:
    revision_id: int
    parent_revision_id: int | None


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_post(
    *,
    title: str | None,
    author: str,
    intent: dict,
    content: str,
) -> tuple[str, str]:
    """
    Creates a new blog post directory and writes meta.yaml, intent.yaml, content.md.

    Returns (post_id, absolute_path).
    """
    timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    ts_str = timestamp.strftime("%Y-%m-%dT%H-%M-%SZ")
    suffix = secrets.token_hex(3)
    post_id = f"{ts_str}__{suffix}"

    post_dir = POSTS_ROOT / post_id
    if post_dir.exists():
        raise FileExistsError(f"Post directory already exists: {post_dir}")

    meta = BlogPostMeta(
        post_id=post_id,
        title=title,
        author=author,
        created_at=timestamp,
        status="draft",
    )

    post_dir.mkdir(parents=True, exist_ok=False)

    meta_path = post_dir / "meta.yaml"
    intent_path = post_dir / "intent.yaml"
    content_path = post_dir / "content.md"

    meta_path.write_text(yaml.safe_dump(meta.model_dump(), sort_keys=False, default_flow_style=False))
    intent_path.write_text(yaml.safe_dump(intent, sort_keys=False, default_flow_style=False))
    content_path.write_text(content)

    return post_id, str(post_dir.resolve())


def list_posts(*, include_drafts: bool = False) -> list[BlogPostMeta]:
    posts: list[BlogPostMeta] = []
    if not POSTS_ROOT.exists() or not POSTS_ROOT.is_dir():
        return []
    for entry in POSTS_ROOT.iterdir():
        if not entry.is_dir():
            continue
        meta_path = entry / "meta.yaml"
        if not meta_path.exists():
            continue
        try:
            meta_data = yaml.safe_load(meta_path.read_text())
            meta = BlogPostMeta.model_validate(meta_data)
        except Exception:
            continue
        if not include_drafts and meta.status != "published":
            continue
        posts.append(meta)
    posts.sort(key=lambda m: m.created_at, reverse=True)
    return posts


def read_post_meta(post_id: str) -> BlogPostMeta:
    post_dir = POSTS_ROOT / post_id
    meta_path = post_dir / "meta.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.yaml not found for post {post_id}")
    try:
        meta_data = yaml.safe_load(meta_path.read_text())
        return BlogPostMeta.model_validate(meta_data)
    except Exception as exc:
        raise ValueError(f"Invalid meta.yaml for post {post_id}: {exc}") from exc


def update_post_status(post_id: str, new_status: str) -> PostStatus:
    post_dir = POSTS_ROOT / post_id
    meta_path = post_dir / "meta.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.yaml not found for post {post_id}")
    meta_payload = yaml.safe_load(meta_path.read_text()) or {}
    if not isinstance(meta_payload, dict):
        raise ValueError(f"Invalid meta.yaml for post {post_id}")

    current_status = require_post_status(meta_payload.get("status"), field="current status")
    resolved_status = require_post_status(new_status, field="new status")
    validate_status_transition(current_status, resolved_status)

    intent_path = post_dir / "intent.yaml"
    if not intent_path.exists():
        raise FileNotFoundError(f"intent.yaml not found for post {post_id}")
    intent_hash = _hash_file(intent_path)

    content_path = post_dir / "content.md"
    content_exists = content_path.exists()
    content_hash = _hash_file(content_path) if content_exists else None

    revisions_before = copy.deepcopy(meta_payload.get("revisions"))

    meta_payload["status"] = resolved_status
    temp_path = meta_path.with_suffix(".yaml.tmp")
    temp_path.write_text(yaml.safe_dump(meta_payload, sort_keys=False, default_flow_style=False))
    os.replace(temp_path, meta_path)

    reloaded = yaml.safe_load(meta_path.read_text()) or {}
    if not isinstance(reloaded, dict):
        raise ValueError(f"Invalid meta.yaml for post {post_id}")
    persisted_status = reloaded.get("status")
    if persisted_status != resolved_status:
        raise ValueError(f"Failed to persist status update for post {post_id}")
    if reloaded.get("revisions") != revisions_before:
        raise ValueError("Status update must not modify revisions metadata")

    if content_exists:
        if not content_path.exists():
            raise ValueError("Status update must not remove content")
        if _hash_file(content_path) != content_hash:
            raise ValueError("Status update must not modify content")
    else:
        if content_path.exists():
            raise ValueError("Status update must not create content")

    if _hash_file(intent_path) != intent_hash:
        raise ValueError("Status update must not modify intent")

    return resolved_status


def read_post_content(post_id: str) -> str:
    post_dir = POSTS_ROOT / post_id
    content_path = post_dir / "content.md"
    if not content_path.exists():
        return _replay_post_content(post_id)
    return content_path.read_text()


def write_post_content(post_id: str, content: str) -> None:
    post_dir = POSTS_ROOT / post_id
    content_path = post_dir / "content.md"
    content_path.write_text(content)


def write_revision_snapshots(
    post_id: str,
    revision_id: int,
    snapshot_chunks: list[dict],
) -> None:
    # Snapshots are artifacts; revision history is authoritative in meta.yaml.
    revisions_dir = POSTS_ROOT / post_id / "revisions"
    revisions_dir.mkdir(parents=True, exist_ok=True)
    for snapshot in snapshot_chunks:
        index = snapshot["index"]
        text = snapshot["text"]
        snapshot_path = revisions_dir / f"{revision_id}_{index}.md"
        snapshot_path.write_text(text)


def apply_blog_update(
    *,
    post_id: str,
    new_content: str,
    delta_type: str,
    source: Literal["policy", "manual", "future"],
    parent_revision_id: int | None,
    delta_payload: dict,
    actor: Any,
    status: str = "applied",
    reason: str | None = None,
    meta_updates: dict | None = None,
) -> RevisionResult:
    post_dir = POSTS_ROOT / post_id
    meta_path = post_dir / "meta.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.yaml not found for post {post_id}")
    meta_payload = yaml.safe_load(meta_path.read_text()) or {}
    if not isinstance(meta_payload, dict):
        raise ValueError(f"Invalid meta.yaml for post {post_id}")
    revisions = meta_payload.get("revisions")
    if revisions is None:
        revisions = []
    elif not isinstance(revisions, list):
        raise ValueError(f"Invalid revisions for post {post_id}")
    existing_revision_ids: list[int] = []
    for entry in revisions:
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid revision entry for post {post_id}")
        revision_id = entry.get("revision_id")
        if not isinstance(revision_id, int):
            raise ValueError(f"Invalid revision_id for post {post_id}")
        existing_revision_ids.append(revision_id)
    last_revision_id = max(existing_revision_ids, default=0)
    next_revision_id = last_revision_id + 1
    if next_revision_id <= last_revision_id:
        raise ValueError(f"Revision id must increase for post {post_id}")
    resolved_parent_revision_id = (
        last_revision_id if parent_revision_id is None and last_revision_id else parent_revision_id
    )
    if (
        resolved_parent_revision_id is not None
        and resolved_parent_revision_id not in existing_revision_ids
    ):
        raise ValueError(f"Invalid parent_revision_id for post {post_id}")
    if last_revision_id and resolved_parent_revision_id is None:
        raise ValueError(f"Missing parent_revision_id for post {post_id}")
    if resolved_parent_revision_id is not None and resolved_parent_revision_id >= next_revision_id:
        raise ValueError(f"Invalid parent_revision_id order for post {post_id}")
    revision_entry: dict[str, Any] = {
        "revision_id": next_revision_id,
        "parent_revision_id": resolved_parent_revision_id,
        "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "delta_type": delta_type,
        "delta_payload": dict(delta_payload),
        "actor": actor,
        "status": status,
        "source": source,
    }
    if reason is not None:
        revision_entry["reason"] = reason
    revisions.append(revision_entry)
    meta_payload["revisions"] = revisions
    if revisions[-1].get("revision_id") != next_revision_id:
        raise ValueError(f"Revision append mismatch for post {post_id}")
    if meta_updates and status == "applied":
        meta_payload.update(meta_updates)
    temp_path = meta_path.with_suffix(".yaml.tmp")
    temp_path.write_text(yaml.safe_dump(meta_payload, sort_keys=False, default_flow_style=False))
    os.replace(temp_path, meta_path)
    if status == "applied" and delta_type in (
        "content_chunks_modified",
        "content_free_edit",
        "content_policy_edit",
    ):
        if not isinstance(new_content, str) or not new_content:
            raise ValueError(f"Applied content delta requires non-empty content for post {post_id}")
        snapshot_chunks = [
            {"index": chunk.index, "text": chunk.text}
            for chunk in split_markdown(new_content)
        ]
        write_revision_snapshots(post_id, next_revision_id, snapshot_chunks)
    return RevisionResult(
        revision_id=next_revision_id,
        parent_revision_id=resolved_parent_revision_id,
    )


def read_revision_metadata(post_id: str) -> list[dict]:
    meta_path = POSTS_ROOT / post_id / "meta.yaml"
    meta_payload = yaml.safe_load(meta_path.read_text()) or {}
    revisions = meta_payload.get("revisions")
    if revisions is None:
        return []
    return revisions


def ensure_draft(post_id: str) -> None:
    meta = read_post_meta(post_id)
    if meta.status != "draft":
        raise RuntimeError(f"Cannot edit non-draft post: {post_id}")


def next_revision_id(post_id: str) -> int:
    raise ValueError("Revision ids must be computed via apply_blog_update only.")


def append_revision_meta(post_id: str, revision_entry: dict) -> None:
    raise ValueError("Revisions must be appended via apply_blog_update only.")


def read_post_intent(post_id: str) -> dict:
    post_dir = POSTS_ROOT / post_id
    intent_path = post_dir / "intent.yaml"
    if not intent_path.exists():
        raise FileNotFoundError(f"intent.yaml not found for post {post_id}")
    try:
        data = yaml.safe_load(intent_path.read_text())
        if not isinstance(data, dict):
            raise ValueError("Intent YAML must be a mapping.")
        return data
    except Exception as exc:
        raise ValueError(f"Invalid intent.yaml for post {post_id}: {exc}") from exc


def _replay_post_content(post_id: str) -> str:
    post_dir = POSTS_ROOT / post_id
    meta_path = post_dir / "meta.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.yaml not found for post {post_id}")
    meta_payload = yaml.safe_load(meta_path.read_text()) or {}
    if not isinstance(meta_payload, dict):
        raise ValueError(f"Invalid meta.yaml for post {post_id}")
    revisions = meta_payload.get("revisions")
    if not isinstance(revisions, list) or not revisions:
        raise ValueError(f"No revisions available to replay content for post {post_id}")

    current_revision_id: int | None = None
    current_payload: dict | None = None

    for entry in revisions:
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid revision entry for post {post_id}")
        if entry.get("status") != "applied":
            continue
        if entry.get("delta_type") not in (
            "content_chunks_modified",
            "content_free_edit",
            "content_policy_edit",
        ):
            continue
        revision_id = entry.get("revision_id")
        if not isinstance(revision_id, int):
            raise ValueError(f"Invalid revision_id for post {post_id}")
        payload = entry.get("delta_payload")
        if not isinstance(payload, dict):
            raise ValueError(f"Invalid delta_payload for post {post_id}")
        current_revision_id = revision_id
        current_payload = payload

    if current_revision_id is None:
        raise ValueError(f"No content deltas available to replay content for post {post_id}")

    revisions_dir = post_dir / "revisions"
    snapshots = sorted(
        revisions_dir.glob(f"{current_revision_id}_*.md"),
        key=lambda p: p.name,
    )
    if not snapshots:
        raise ValueError(f"Missing snapshots for revision {current_revision_id} in post {post_id}")

    chunks_by_index: dict[int, str] = {}
    for snapshot_path in snapshots:
        stem = snapshot_path.stem
        if "_" not in stem:
            raise ValueError(f"Invalid snapshot filename {snapshot_path}")
        revision_str, index_str = stem.split("_", 1)
        if revision_str != str(current_revision_id) or not index_str.isdigit():
            raise ValueError(f"Invalid snapshot filename {snapshot_path}")
        index = int(index_str)
        chunks_by_index[index] = snapshot_path.read_text()

    max_index = max(chunks_by_index)
    expected_indices = list(range(max_index + 1))
    if sorted(chunks_by_index.keys()) != expected_indices:
        raise ValueError(f"Snapshot indices must be contiguous for post {post_id}")

    chunks = [
        Chunk(
            index=i,
            text=chunks_by_index[i],
            trailing_separator="\n\n" if i < max_index else "",
        )
        for i in range(max_index + 1)
    ]
    content = join_chunks(chunks)
    content_path = post_dir / "content.md"
    replay_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    if content_path.exists():
        on_disk_hash = hashlib.sha256(content_path.read_text().encode("utf-8")).hexdigest()
        if on_disk_hash != replay_hash:
            raise ValueError(
                f"Revision replay content mismatch for post {post_id} at revision {current_revision_id}"
            )
    after_hash = None if current_payload is None else current_payload.get("after_hash")
    if isinstance(after_hash, str):
        if replay_hash != after_hash:
            raise ValueError(
                f"Revision replay hash mismatch for post {post_id} at revision {current_revision_id}"
            )
    content_path.write_text(content)
    return content


def _migrate_legacy_revisions(post_id: str) -> None:
    # Revision files are non-authoritative artifacts; do not infer metadata.
    return
    post_dir = POSTS_ROOT / post_id
    meta_path = post_dir / "meta.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.yaml not found for post {post_id}")
    meta_payload = yaml.safe_load(meta_path.read_text()) or {}
    if not isinstance(meta_payload, dict):
        raise ValueError(f"Invalid meta.yaml for post {post_id}")

    revisions = meta_payload.get("revisions")
    existing_revisions: list[dict] = []
    if revisions is not None:
        if not isinstance(revisions, list):
            raise ValueError(f"Invalid revisions for post {post_id}")
        for entry in revisions:
            if not isinstance(entry, dict):
                raise ValueError(f"Invalid revision entry for post {post_id}")
            existing_revisions.append(dict(entry))

    snapshots_by_revision = _load_snapshot_groups(
        post_dir,
        [entry["revision_id"] for entry in existing_revisions],
    )

    revisions_by_id: dict[int, dict] = {}
    for entry in existing_revisions:
        revision_id = entry.get("revision_id")
        if not isinstance(revision_id, int):
            raise ValueError(f"Invalid revision_id for post {post_id}")
        revisions_by_id[revision_id] = entry

    needs_migration = False
    for revision_id, snapshot_chunks in snapshots_by_revision.items():
        entry = revisions_by_id.get(revision_id)
        if entry is None:
            needs_migration = True
            continue
        delta_type = entry.get("delta_type")
        if delta_type != "content_chunks_modified":
            needs_migration = True

    if not needs_migration:
        return

    for revision_id, snapshot_chunks in snapshots_by_revision.items():
        entry = revisions_by_id.get(revision_id)
        if entry is None or entry.get("delta_type") != "content_chunks_modified":
            content, after_hash = _build_content_from_snapshots(snapshot_chunks)
            entry = {
                "revision_id": revision_id,
                "delta_type": "content_chunks_modified",
                "delta_payload": {
                    "changed_chunks": list(range(len(snapshot_chunks))),
                    "before_hash": None,
                    "after_hash": after_hash,
                },
                "status": "applied",
                "actor": {"type": "migration", "id": "legacy"},
            }
            revisions_by_id[revision_id] = entry

    migrated = [revisions_by_id[rid] for rid in sorted(revisions_by_id)]
    meta_payload["revisions"] = migrated
    meta_path.write_text(yaml.safe_dump(meta_payload, sort_keys=False, default_flow_style=False))


def _load_snapshot_groups(post_dir: Path, revision_ids: list[int]) -> dict[int, dict[int, str]]:
    revisions_dir = post_dir / "revisions"
    if not revisions_dir.exists():
        return {}
    snapshots_by_revision: dict[int, dict[int, str]] = {}
    for revision_id in revision_ids:
        for snapshot_path in revisions_dir.glob(f"{revision_id}_*.md"):
            stem = snapshot_path.stem
            if "_" not in stem:
                raise ValueError(f"Invalid snapshot filename {snapshot_path}")
            revision_str, index_str = stem.split("_", 1)
            if revision_str != str(revision_id) or not index_str.isdigit():
                raise ValueError(f"Invalid snapshot filename {snapshot_path}")
            index = int(index_str)
            snapshots_by_revision.setdefault(revision_id, {})[index] = snapshot_path.read_text()
    return snapshots_by_revision


def _build_content_from_snapshots(snapshot_chunks: dict[int, str]) -> tuple[str, str]:
    if not snapshot_chunks:
        raise ValueError("No snapshot chunks available")
    max_index = max(snapshot_chunks)
    expected_indices = list(range(max_index + 1))
    if sorted(snapshot_chunks.keys()) != expected_indices:
        raise ValueError("Snapshot indices must be contiguous")
    chunks = [
        Chunk(
            index=i,
            text=snapshot_chunks[i],
            trailing_separator="\n\n" if i < max_index else "",
        )
        for i in range(max_index + 1)
    ]
    content = join_chunks(chunks)
    after_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    return content, after_hash
