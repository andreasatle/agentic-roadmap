from datetime import datetime, timezone
import hashlib
import secrets
from pathlib import Path

import yaml

from apps.blog.types import BlogPostMeta
from document_writer.domain.editor.chunking import Chunk, join_chunks


def create_post(
    *,
    title: str | None,
    author: str,
    intent: dict,
    content: str,
    posts_root: str = "posts",
) -> tuple[str, str]:
    """
    Creates a new blog post directory and writes meta.yaml, intent.yaml, content.md.

    Returns (post_id, absolute_path).
    """
    timestamp = datetime.now(timezone.utc).replace(microsecond=0)
    ts_str = timestamp.strftime("%Y-%m-%dT%H-%M-%SZ")
    suffix = secrets.token_hex(3)
    post_id = f"{ts_str}__{suffix}"

    root = Path(posts_root)
    post_dir = root / post_id
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


def list_posts(*, posts_root: str = "posts", include_drafts: bool = False) -> list[BlogPostMeta]:
    posts: list[BlogPostMeta] = []
    root = Path(posts_root)
    if not root.exists() or not root.is_dir():
        return []
    for entry in root.iterdir():
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


def _post_dir(post_id: str, posts_root: str) -> Path:
    return Path(posts_root) / post_id


def read_post_meta(post_id: str, posts_root: str = "posts") -> BlogPostMeta:
    post_dir = _post_dir(post_id, posts_root)
    meta_path = post_dir / "meta.yaml"
    if not meta_path.exists():
        raise FileNotFoundError(f"meta.yaml not found for post {post_id}")
    try:
        meta_data = yaml.safe_load(meta_path.read_text())
        return BlogPostMeta.model_validate(meta_data)
    except Exception as exc:
        raise ValueError(f"Invalid meta.yaml for post {post_id}: {exc}") from exc


def read_post_content(post_id: str, posts_root: str = "posts") -> str:
    post_dir = _post_dir(post_id, posts_root)
    content_path = post_dir / "content.md"
    if not content_path.exists():
        return _replay_post_content(post_id, posts_root)
    return content_path.read_text()


def write_post_content(post_id: str, content: str, posts_root: str = "posts") -> None:
    post_dir = _post_dir(post_id, posts_root)
    content_path = post_dir / "content.md"
    content_path.write_text(content)


def ensure_draft(post_id: str, posts_root: str = "posts") -> None:
    meta = read_post_meta(post_id, posts_root)
    if meta.status != "draft":
        raise RuntimeError(f"Cannot edit non-draft post: {post_id}")


def next_revision_id(post_id: str, posts_root: str = "posts") -> int:
    post_dir = _post_dir(post_id, posts_root)
    meta_path = post_dir / "meta.yaml"
    if meta_path.exists():
        meta_payload = yaml.safe_load(meta_path.read_text()) or {}
        if not isinstance(meta_payload, dict):
            raise ValueError(f"Invalid meta.yaml for post {post_id}")
        revisions = meta_payload.get("revisions")
        if revisions is not None:
            if not isinstance(revisions, list):
                raise ValueError(f"Invalid revisions for post {post_id}")
            revision_ids: list[int] = []
            for entry in revisions:
                if not isinstance(entry, dict):
                    raise ValueError(f"Invalid revision entry for post {post_id}")
                revision_id = entry.get("revision_id")
                if not isinstance(revision_id, int):
                    raise ValueError(f"Invalid revision_id for post {post_id}")
                revision_ids.append(revision_id)
            return max(revision_ids, default=0) + 1
    revisions_dir = post_dir / "revisions"
    if not revisions_dir.exists():
        return 1
    revision_ids: list[int] = []
    for entry in revisions_dir.glob("*.md"):
        stem = entry.stem
        if "_" in stem:
            stem = stem.split("_", 1)[0]
        if stem.isdigit():
            revision_ids.append(int(stem))
    return max(revision_ids, default=0) + 1


def append_revision_meta(post_id: str, revision_entry: dict, posts_root: str = "posts") -> None:
    raise NotImplementedError(
        "Revisions must be appended via PostRevisionWriter.apply_delta."
    )


def read_post_intent(post_id: str, posts_root: str = "posts") -> dict:
    post_dir = _post_dir(post_id, posts_root)
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


def _replay_post_content(post_id: str, posts_root: str) -> str:
    post_dir = _post_dir(post_id, posts_root)
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


def _migrate_legacy_revisions(post_id: str, posts_root: str) -> None:
    post_dir = _post_dir(post_id, posts_root)
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

    snapshots_by_revision = _load_snapshot_groups(post_dir)

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


def _load_snapshot_groups(post_dir: Path) -> dict[int, dict[int, str]]:
    revisions_dir = post_dir / "revisions"
    if not revisions_dir.exists():
        return {}
    snapshots_by_revision: dict[int, dict[int, str]] = {}
    for snapshot_path in revisions_dir.glob("*.md"):
        stem = snapshot_path.stem
        if "_" not in stem:
            raise ValueError(f"Invalid snapshot filename {snapshot_path}")
        revision_str, index_str = stem.split("_", 1)
        if not revision_str.isdigit() or not index_str.isdigit():
            raise ValueError(f"Invalid snapshot filename {snapshot_path}")
        revision_id = int(revision_str)
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
