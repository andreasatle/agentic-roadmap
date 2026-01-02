from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from apps.legal_document_ingest.reconstruction.lines import ReconstructedLine


class CorrectionRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    type: Literal["SYMBOL_REPAIR", "HYPHENATION_REPAIR", "LEXICON_FIX"]
    before: str
    after: str
    token_ids: list[str]


class CorrectedLine(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    text: str
    token_ids: list[str]
    page_number: int
    corrections: list[CorrectionRecord]


def apply_allowed_corrections(
    lines: list[ReconstructedLine],
) -> list[CorrectedLine]:
    lexicon: dict[str, str] = {}
    corrected: list[CorrectedLine] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        text = line.text
        corrections: list[CorrectionRecord] = []

        symbol_repaired = _apply_symbol_repairs(text)
        if symbol_repaired != text:
            corrections.append(
                CorrectionRecord(
                    type="SYMBOL_REPAIR",
                    before=text,
                    after=symbol_repaired,
                    token_ids=list(line.token_ids),
                )
            )
            text = symbol_repaired

        lexicon_repaired = lexicon.get(text)
        if lexicon_repaired is not None and lexicon_repaired != text:
            corrections.append(
                CorrectionRecord(
                    type="LEXICON_FIX",
                    before=text,
                    after=lexicon_repaired,
                    token_ids=list(line.token_ids),
                )
            )
            text = lexicon_repaired

        if text.endswith("-") and i + 1 < len(lines):
            next_line = lines[i + 1]
            if next_line.page_number == line.page_number:
                before = text + next_line.text
                after = text[:-1] + next_line.text
                corrections.append(
                    CorrectionRecord(
                        type="HYPHENATION_REPAIR",
                        before=before,
                        after=after,
                        token_ids=list(line.token_ids) + list(next_line.token_ids),
                    )
                )
                corrected.append(
                    CorrectedLine(
                        text=after,
                        token_ids=list(line.token_ids) + list(next_line.token_ids),
                        page_number=line.page_number,
                        corrections=corrections,
                    )
                )
                i += 2
                continue

        corrected.append(
            CorrectedLine(
                text=text,
                token_ids=list(line.token_ids),
                page_number=line.page_number,
                corrections=corrections,
            )
        )
        i += 1
    return corrected


def _apply_symbol_repairs(text: str) -> str:
    replacements = {
        "º": "°",
        "′": "'",
        "″": '"',
    }
    out = text
    for before, after in replacements.items():
        out = out.replace(before, after)
    return out
