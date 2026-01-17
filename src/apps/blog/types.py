from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel

PostStatus = Literal["draft", "published", "archived"]
POST_STATUS_VALUES: tuple[str, ...] = get_args(PostStatus)
POST_STATUS_TRANSITIONS: dict[PostStatus, tuple[PostStatus, ...]] = {
    "draft": ("published", "archived"),
    "published": ("archived",),
    "archived": (),
}


def require_post_status(value: object, *, field: str = "status") -> PostStatus:
    if not isinstance(value, str) or value not in POST_STATUS_VALUES:
        raise ValueError(f"{field} must be one of {', '.join(POST_STATUS_VALUES)}")
    return value


def resolve_post_status(value: object, *, field: str = "status") -> PostStatus:
    if value is None:
        return "draft"
    return require_post_status(value, field=field)


def validate_status_transition(from_status: PostStatus, to_status: PostStatus) -> None:
    allowed = POST_STATUS_TRANSITIONS.get(from_status, ())
    if to_status not in allowed:
        raise ValueError(f"Invalid status transition: {from_status} -> {to_status}")


class BlogPostMeta(BaseModel):
    post_id: str
    title: str | None = None
    author: str
    created_at: datetime
    status: PostStatus = "draft"
