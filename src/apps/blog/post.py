from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel

from apps.blog.storage import create_post


class BlogPost(BaseModel):
    title: str | None = None
    author: str
    intent: dict
    content: str
    status: Literal["draft", "published"] = "draft"
    created_at: datetime | None = None

    def persist(self, posts_root: str = "posts") -> tuple[str, str]:
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).replace(microsecond=0)
        return create_post(
            title=self.title,
            author=self.author,
            intent=self.intent,
            content=self.content,
            posts_root=posts_root,
        )
