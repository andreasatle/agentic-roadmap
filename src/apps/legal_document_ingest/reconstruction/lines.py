from __future__ import annotations

import statistics

from pydantic import BaseModel, ConfigDict

from apps.legal_document_ingest.ocr.models import EvidenceBundle, OcrToken


class ReconstructedLine(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    text: str
    token_ids: list[str]
    page_number: int


def reconstruct_lines(
    bundle: EvidenceBundle,
    token_ids: list[str],
) -> list[ReconstructedLine]:
    token_index, page_stats = _index_tokens(bundle)
    lines: list[ReconstructedLine] = []
    current_tokens: list[OcrToken] = []
    current_token_ids: list[str] = []
    current_text_parts: list[str] = []
    current_page: int | None = None
    reference_y0: float | None = None
    prev_token: OcrToken | None = None

    for token_id in token_ids:
        entry = token_index.get(token_id)
        if entry is None:
            raise KeyError(f"Token id not found in EvidenceBundle: {token_id}")
        token, page_number = entry

        if current_page is None:
            _start_line(
                token,
                page_number,
                current_tokens,
                current_token_ids,
                current_text_parts,
            )
            current_page = page_number
            reference_y0 = token.bbox.y0
            prev_token = token
            continue

        if page_number != current_page:
            _flush_line(lines, current_tokens, current_token_ids, current_text_parts, current_page)
            current_tokens = []
            current_token_ids = []
            current_text_parts = []
            _start_line(
                token,
                page_number,
                current_tokens,
                current_token_ids,
                current_text_parts,
            )
            current_page = page_number
            reference_y0 = token.bbox.y0
            prev_token = token
            continue

        stats = page_stats.get(page_number)
        if stats is None:
            _flush_line(lines, current_tokens, current_token_ids, current_text_parts, current_page)
            current_tokens = []
            current_token_ids = []
            current_text_parts = []
            _start_line(
                token,
                page_number,
                current_tokens,
                current_token_ids,
                current_text_parts,
            )
            current_page = page_number
            reference_y0 = token.bbox.y0
            prev_token = token
            continue

        vertical_tol = max(3.0, 0.25 * stats.median_token_height)
        if reference_y0 is None or abs(token.bbox.y0 - reference_y0) > vertical_tol:
            _flush_line(lines, current_tokens, current_token_ids, current_text_parts, current_page)
            current_tokens = []
            current_token_ids = []
            current_text_parts = []
            _start_line(
                token,
                page_number,
                current_tokens,
                current_token_ids,
                current_text_parts,
            )
            current_page = page_number
            reference_y0 = token.bbox.y0
            prev_token = token
            continue

        if prev_token is not None and stats.median_char_width > 0:
            if (token.bbox.x0 - prev_token.bbox.x1) > stats.median_char_width:
                current_text_parts.append(" ")
        current_tokens.append(token)
        current_token_ids.append(token_id)
        current_text_parts.append(token.text)
        prev_token = token

    if current_page is not None and current_tokens:
        _flush_line(lines, current_tokens, current_token_ids, current_text_parts, current_page)

    return lines


def _start_line(
    token: OcrToken,
    page_number: int,
    current_tokens: list[OcrToken],
    current_token_ids: list[str],
    current_text_parts: list[str],
) -> None:
    current_tokens.append(token)
    current_token_ids.append(token.token_id)
    current_text_parts.append(token.text)


def _flush_line(
    lines: list[ReconstructedLine],
    current_tokens: list[OcrToken],
    current_token_ids: list[str],
    current_text_parts: list[str],
    page_number: int,
) -> None:
    lines.append(
        ReconstructedLine(
            text="".join(current_text_parts),
            token_ids=list(current_token_ids),
            page_number=page_number,
        )
    )


def _index_tokens(
    bundle: EvidenceBundle,
) -> tuple[dict[str, tuple[OcrToken, int]], dict[int, _PageStats]]:
    token_index: dict[str, tuple[OcrToken, int]] = {}
    page_heights: dict[int, list[float]] = {}
    page_char_widths: dict[int, list[float]] = {}

    for run in bundle.ocr_runs:
        for page in run.pages:
            for token in page.tokens:
                token_index[token.token_id] = (token, page.page_number)
                height = float(token.bbox.y1 - token.bbox.y0)
                page_heights.setdefault(page.page_number, []).append(height)
                if token.text:
                    width = float(token.bbox.x1 - token.bbox.x0)
                    page_char_widths.setdefault(page.page_number, []).append(
                        width / max(len(token.text), 1)
                    )

    page_stats: dict[int, _PageStats] = {}
    for page_number, heights in page_heights.items():
        median_height = float(statistics.median(heights)) if heights else 0.0
        widths = page_char_widths.get(page_number, [])
        median_width = float(statistics.median(widths)) if widths else 0.0
        page_stats[page_number] = _PageStats(median_height, median_width)

    return token_index, page_stats


class _PageStats(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    median_token_height: float
    median_char_width: float
