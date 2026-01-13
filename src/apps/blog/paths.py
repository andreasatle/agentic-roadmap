"""Single canonical filesystem root for blog posts.

POSTS_ROOT is the single canonical filesystem root for all blog storage.
No other module may define, derive, or override a blog posts root.
"""

from pathlib import Path

POSTS_ROOT = Path(__file__).resolve().parent / "posts"

__all__ = ["POSTS_ROOT"]
