"""Authoritative single-writer interface for post revision state."""

from pathlib import Path
from typing import Any

from apps.blog.paths import POSTS_ROOT
from apps.blog.storage import apply_blog_update, read_post_content


class PostRevisionWriter:
    """Single-writer authority for loading and revising blog entries.

    This module centralizes revision recording and content updates under a
    single-writer authority.
    """

    def __init__(self, posts_root: str | None = None) -> None:
        self.posts_root = Path(posts_root) if posts_root is not None else POSTS_ROOT

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
        new_content: str | None = None,
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
        if delta_type == "status_changed":
            raise ValueError("Status updates must not be recorded as revisions")
        mutation_delta_types = {
            "content_chunks_modified",
            "content_free_edit",
            "content_policy_edit",
            "title_changed",
            "author_changed",
            "title_set",
        }
        if delta_type not in mutation_delta_types:
            raise ValueError(f"Unknown delta_type: {delta_type}")
        record_payload = dict(delta_payload)
        content_requires_new_content = {
            "content_free_edit",
            "content_policy_edit",
        }
        if delta_type in content_requires_new_content and new_content is None:
            raise ValueError(f"{delta_type} requires new_content")
        meta_updates = None
        if delta_type == "title_changed":
            new_title = record_payload.get("new_title")
            if not isinstance(new_title, str):
                raise ValueError("title_changed requires delta_payload.new_title as string")
            if status == "applied":
                meta_updates = {"title": new_title}
        if delta_type == "author_changed":
            new_author = record_payload.get("new_author")
            if not isinstance(new_author, str):
                raise ValueError("author_changed requires delta_payload.new_author as string")
            if status == "applied":
                meta_updates = {"author": new_author}
        actor_type = actor.get("type") if isinstance(actor, dict) else None
        if actor_type == "policy":
            source = "policy"
        elif actor_type == "human":
            source = "manual"
        else:
            source = "future"
        resolved_content = (
            new_content
            if new_content is not None
            else read_post_content(post_id, self.posts_root)
        )
        revision_result = apply_blog_update(
            post_id=post_id,
            new_content=resolved_content,
            delta_type=delta_type,
            source=source,
            parent_revision_id=None,
            delta_payload=record_payload,
            actor=actor,
            status=status,
            reason=reason,
            meta_updates=meta_updates,
            posts_root=self.posts_root,
        )
        return revision_result.revision_id

    def get_current_state(self, post_id: str) -> Any:
        """Return the current authoritative state for a post."""
        raise NotImplementedError

    def get_revision_log(self, post_id: str) -> Any:
        """Return the authoritative revision log for a post."""
        raise NotImplementedError
