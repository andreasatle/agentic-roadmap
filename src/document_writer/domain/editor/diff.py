from dataclasses import dataclass
from difflib import SequenceMatcher


@dataclass(frozen=True)
class DiffResult:
    added_lines: int
    removed_lines: int
    changed_lines: int
    total_lines: int


def diff_lines(before: str, after: str) -> DiffResult:
    before_lines = before.split("\n")
    after_lines = after.split("\n")
    matcher = SequenceMatcher(a=before_lines, b=after_lines)

    added = 0
    removed = 0
    changed = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            added += (j2 - j1)
        elif tag == "delete":
            removed += (i2 - i1)
        elif tag == "replace":
            changed += max(i2 - i1, j2 - j1)

    return DiffResult(
        added_lines=added,
        removed_lines=removed,
        changed_lines=changed,
        total_lines=len(before_lines),
    )
