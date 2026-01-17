import hashlib
from pathlib import Path

import pytest
import yaml

from apps.blog import storage
from apps.blog.storage import create_post, update_post_status
from apps.blog.types import validate_status_transition


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture()
def posts_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "posts"
    root.mkdir()
    monkeypatch.setattr(storage, "POSTS_ROOT", root)
    return root


def test_validate_status_transition_allows_valid() -> None:
    validate_status_transition("draft", "published")
    validate_status_transition("draft", "archived")
    validate_status_transition("published", "archived")


def test_validate_status_transition_rejects_invalid() -> None:
    with pytest.raises(ValueError):
        validate_status_transition("published", "draft")
    with pytest.raises(ValueError):
        validate_status_transition("archived", "published")
    with pytest.raises(ValueError):
        validate_status_transition("draft", "draft")


def test_status_update_preserves_content_intent_and_revisions(posts_root: Path) -> None:
    post_id, _ = create_post(
        title="Status invariant",
        author="tester",
        intent={"purpose": "check"},
        content="Alpha\n\nBeta",
    )

    post_dir = posts_root / post_id
    content_path = post_dir / "content.md"
    intent_path = post_dir / "intent.yaml"
    meta_path = post_dir / "meta.yaml"

    content_hash = _hash_file(content_path)
    intent_hash = _hash_file(intent_path)

    update_post_status(post_id, "published")

    meta_payload = yaml.safe_load(meta_path.read_text())
    assert meta_payload["status"] == "published"
    assert "revisions" not in meta_payload
    assert _hash_file(content_path) == content_hash
    assert _hash_file(intent_path) == intent_hash


def test_status_update_rejects_unknown_status(posts_root: Path) -> None:
    post_id, _ = create_post(
        title="Status invalid",
        author="tester",
        intent={},
        content="Alpha",
    )

    with pytest.raises(ValueError):
        update_post_status(post_id, "invalid-status")

    meta_payload = yaml.safe_load((posts_root / post_id / "meta.yaml").read_text())
    assert meta_payload["status"] == "draft"


def test_archived_rejects_further_transitions(posts_root: Path) -> None:
    post_id, _ = create_post(
        title="Archive me",
        author="tester",
        intent={},
        content="Alpha",
    )

    update_post_status(post_id, "archived")

    with pytest.raises(ValueError):
        update_post_status(post_id, "published")

    meta_payload = yaml.safe_load((posts_root / post_id / "meta.yaml").read_text())
    assert meta_payload["status"] == "archived"
