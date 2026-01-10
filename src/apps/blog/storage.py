from datetime import datetime, timezone
import secrets
from pathlib import Path

import yaml

from apps.blog.types import BlogPostMeta


class TitleAlreadySetError(ValueError):
    pass


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
        raise FileNotFoundError(f"content.md not found for post {post_id}")
    return content_path.read_text()


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


def set_post_title(post_id: str, title: str, posts_root: str = "posts") -> BlogPostMeta:
    clean_title = (title or "").strip()
    if not clean_title:
        raise ValueError("Title must be a non-empty string")
    meta = read_post_meta(post_id, posts_root)
    existing_title = (meta.title or "").strip()
    if existing_title:
        raise TitleAlreadySetError("Title already set")
    meta.title = clean_title
    post_dir = _post_dir(post_id, posts_root)
    meta_path = post_dir / "meta.yaml"
    meta_path.write_text(yaml.safe_dump(meta.model_dump(), sort_keys=False, default_flow_style=False))
    return meta
