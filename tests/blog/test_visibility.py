from pathlib import Path

import pytest

from apps.blog import storage
from apps.blog.storage import create_post, list_posts, update_post_status


@pytest.fixture()
def posts_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "posts"
    root.mkdir()
    monkeypatch.setattr(storage, "POSTS_ROOT", root)
    return root


def test_list_posts_visibility_filters(posts_root: Path) -> None:
    draft_id, _ = create_post(
        title="Draft",
        author="tester",
        intent={},
        content="Draft content",
    )
    published_id, _ = create_post(
        title="Published",
        author="tester",
        intent={},
        content="Published content",
    )
    update_post_status(published_id, "published")
    archived_id, _ = create_post(
        title="Archived",
        author="tester",
        intent={},
        content="Archived content",
    )
    update_post_status(archived_id, "published")
    update_post_status(archived_id, "archived")

    public_posts = list_posts(visibility="public")
    public_ids = {post.post_id for post in public_posts}
    assert published_id in public_ids
    assert draft_id not in public_ids
    assert archived_id not in public_ids

    editor_posts = list_posts(visibility="editor")
    editor_ids = {post.post_id for post in editor_posts}
    assert draft_id in editor_ids
    assert published_id in editor_ids
    assert archived_id in editor_ids
