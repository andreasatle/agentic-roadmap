from dataclasses import dataclass

from document_writer.domain.editor.diff import diff_lines


@dataclass(frozen=True)
class ValidationResult:
    accepted: bool
    reason: str | None


def _count_paragraph_breaks(text: str) -> int:
    return text.count("\n\n")


def validate_diff(
    *,
    before: str,
    after: str,
    policy_text: str,
) -> ValidationResult:
    if before == after:
        return ValidationResult(accepted=True, reason=None)

    if before.strip() and not after.strip():
        return ValidationResult(accepted=False, reason="full_chunk_deletion")

    if _count_paragraph_breaks(after) > _count_paragraph_breaks(before):
        return ValidationResult(accepted=False, reason="new_paragraphs")

    if before.strip() == after.strip():
        return ValidationResult(accepted=False, reason="whitespace_only_change")

    diff = diff_lines(before, after)

    if diff.added_lines > 0:
        return ValidationResult(accepted=False, reason="added_lines")

    total_lines = max(diff.total_lines, 1)
    if (diff.changed_lines / total_lines) > 0.2:
        return ValidationResult(accepted=False, reason="change_ratio_exceeded")

    return ValidationResult(accepted=True, reason=None)
