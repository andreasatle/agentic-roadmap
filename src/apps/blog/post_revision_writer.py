"""Authoritative single-writer interface for post revision state."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


class PostRevisionWriter:
    """Single-writer authority for loading and revising blog posts.

    This module centralizes revision recording and content updates under a
    single-writer authority.
    """

    def __init__(self, posts_root: str = "posts") -> None:
        self._posts_root = posts_root

    def load_post(self, post_id: str) -> Any:
        """Load a post into the writer's authority context for revision."""
        raise NotImplementedError

    def apply_delta(
        self,
        post_id: str,
        *,
        actor: Any,
        delta_type: str,
        delta_payload: dict,
        reason: str | None = None,
        status: str = "applied",  # TEMP: supports explicit rejected deltas until formal validation exists.
    ) -> Any:
        """Apply a delta under single-writer authority and record intent."""
        forbidden_keys = {"status", "_content", "_snapshot_chunks"}
        present_forbidden = forbidden_keys.intersection(delta_payload.keys())
        if present_forbidden:
            raise ValueError(
                "delta_payload contains forbidden keys: "
                + ", ".join(sorted(present_forbidden))
            )
        if status not in ("applied", "rejected"):
            raise ValueError(f"Unknown status: {status}")
        record_payload = dict(delta_payload)

        post_dir = Path(self._posts_root) / post_id
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

        last_revision_id = 0
        if revisions:
            last_entry = revisions[-1]
            if not isinstance(last_entry, dict):
                raise ValueError(f"Invalid revision entry for post {post_id}")
            last_revision_id = last_entry.get("revision_id", 0)
            if not isinstance(last_revision_id, int):
                raise ValueError(f"Invalid revision_id for post {post_id}")

        revision_id = last_revision_id + 1
        revision_entry: dict[str, Any] = {
            "revision_id": revision_id,
            "timestamp": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
            "delta_type": delta_type,
            "delta_payload": record_payload,
            "actor": actor,
            "status": status,
        }
        if reason is not None:
            revision_entry["reason"] = reason

        if delta_type == "title_changed" and status == "applied":
            new_title = record_payload.get("new_title")
            if not isinstance(new_title, str):
                raise ValueError("title_changed requires delta_payload.new_title as string")
            meta_payload["title"] = new_title
        revisions.append(revision_entry)
        meta_payload["revisions"] = revisions
        meta_path.write_text(yaml.safe_dump(meta_payload, sort_keys=False, default_flow_style=False))

        return revision_id

    def get_current_state(self, post_id: str) -> Any:
        """Return the current authoritative state for a post."""
        raise NotImplementedError

    def get_revision_log(self, post_id: str) -> Any:
        """Return the authoritative revision log for a post."""
        raise NotImplementedError
