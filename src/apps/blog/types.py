from datetime import datetime
from typing import Literal, get_args

from pydantic import BaseModel

PostStatus = Literal["draft", "published", "archived"]
POST_STATUS_VALUES: tuple[str, ...] = get_args(PostStatus)


class BlogPostMeta(BaseModel):
    post_id: str
    title: str | None = None
    author: str
    created_at: datetime
    status: PostStatus
