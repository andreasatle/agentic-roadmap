"""Derived-state model for blog posts with deterministic delta reduction."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal, Mapping, TypedDict, Any

from apps.blog.types import PostStatus, POST_STATUS_VALUES


DeltaStatus = Literal["applied", "rejected"]


class RevisionDelta(TypedDict):
    delta_type: str
    delta_payload: dict
    status: DeltaStatus
    revision_id: int


@dataclass(frozen=True)
class PostDerivedState:
    """Normative derived state for a blog post.

    Invariants:
    - Derived-only state, no persistence or I/O.
    - Rejected deltas do not change state.
    - Applied deltas advance revision_id exactly once.
    """

    post_id: str
    title: str | None
    author: str | None
    status: PostStatus
    content_ref: str | None
    revision_id: int

    def apply_delta(self, delta: RevisionDelta) -> "PostDerivedState":
        """Apply a single delta and return the next derived state."""
        if delta["status"] == "rejected":
            return self
        if delta["status"] != "applied":
            raise ValueError(f"Unknown delta status: {delta['status']}")

        next_revision_id = delta["revision_id"]
        if next_revision_id != self.revision_id + 1:
            raise ValueError(
                f"Delta revision_id {next_revision_id} does not advance state "
                f"from {self.revision_id}"
            )

        delta_type = delta["delta_type"]
        payload = delta["delta_payload"]

        if delta_type in ("content_chunks_modified", "content_free_edit", "content_policy_edit"):
            content_ref = _require_str(payload, "after_hash")
            return replace(self, content_ref=content_ref, revision_id=next_revision_id)
        if delta_type == "title_changed":
            title = _require_str_or_none(payload, "new_title")
            return replace(self, title=title, revision_id=next_revision_id)
        if delta_type == "author_changed":
            author = _require_str(payload, "new_author")
            return replace(self, author=author, revision_id=next_revision_id)
        if delta_type == "title_set":
            title = _require_str_or_none(payload, "title")
            return replace(self, title=title, revision_id=next_revision_id)
        if delta_type == "status_changed":
            status = _require_status(payload, "status")
            return replace(self, status=status, revision_id=next_revision_id)

        raise ValueError(f"Unknown delta_type: {delta_type}")


def replay_deltas(initial: PostDerivedState, deltas: list[RevisionDelta]) -> PostDerivedState:
    """Reduce a list of deltas into a final PostDerivedState deterministically."""
    state = initial
    for delta in deltas:
        state = state.apply_delta(delta)
    return state


def _require_str(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"Delta payload must include non-empty '{key}'")
    return value


def _require_str_or_none(payload: Mapping[str, Any], key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Delta payload '{key}' must be a string or None")
    return value


def _require_status(payload: Mapping[str, Any], key: str) -> PostStatus:
    value = payload.get(key)
    if value not in POST_STATUS_VALUES:
        raise ValueError(
            f"Delta payload '{key}' must be one of {', '.join(POST_STATUS_VALUES)}"
        )
    return value
