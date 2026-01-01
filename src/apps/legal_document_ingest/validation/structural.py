from __future__ import annotations

import statistics
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from apps.legal_document_ingest.detection.spans import CandidateSpan
from apps.legal_document_ingest.ocr.models import EvidenceBundle, OcrToken


class ValidatedSpan(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    span: CandidateSpan
    is_valid: bool
    validation_failures: list[str]


@dataclass(frozen=True)
class _PageStats:
    median_token_height: float
    median_char_width: float


def validate_candidate_spans(
    bundle: EvidenceBundle,
    ordered_token_ids: list[str],
    spans: list[CandidateSpan],
) -> list[ValidatedSpan]:
    token_index, page_stats = _index_tokens(bundle)
    ordered_index = {token_id: idx for idx, token_id in enumerate(ordered_token_ids)}
    anchor_token_ids = _collect_anchor_token_ids(spans)

    results: list[ValidatedSpan] = []

    for span in spans:
        failures: list[str] = []

        if len(span.token_ids) < 10:
            failures.append("SPAN_TOO_SHORT")

        if span.page_end < span.page_start or (span.page_end - span.page_start) > 3:
            failures.append("PAGE_GAP")

        if not _is_contiguous(span.token_ids, ordered_index):
            failures.append("NON_CONTIGUOUS")

        if span.start_token_id in anchor_token_ids:
            failures.append("ANCHOR_OVERLAP")

        if _has_missing_tokens(span.token_ids, token_index):
            failures.append("TOKEN_NOT_FOUND")
        else:
            if _low_confidence_density(span.token_ids, token_index):
                failures.append("LOW_CONFIDENCE_DENSITY")
            if _contains_heading_line(span.token_ids, token_index, page_stats):
                failures.append("HEADING_INTRUSION")

        results.append(
            ValidatedSpan(
                span=span,
                is_valid=not failures,
                validation_failures=failures,
            )
        )

    return results


def _collect_anchor_token_ids(spans: list[CandidateSpan]) -> set[str]:
    anchor_token_ids: set[str] = set()
    for span in spans:
        anchor_token_ids.update(span.anchor.token_ids)
    return anchor_token_ids


def _is_contiguous(
    token_ids: list[str], ordered_index: dict[str, int]
) -> bool:
    if not token_ids:
        return False
    try:
        start = ordered_index[token_ids[0]]
    except KeyError:
        return False
    for offset, token_id in enumerate(token_ids):
        if ordered_index.get(token_id) != start + offset:
            return False
    return True


def _has_missing_tokens(
    token_ids: list[str], token_index: dict[str, tuple[OcrToken, int]]
) -> bool:
    for token_id in token_ids:
        if token_id not in token_index:
            return True
    return False


def _low_confidence_density(
    token_ids: list[str], token_index: dict[str, tuple[OcrToken, int]]
) -> bool:
    if len(token_ids) < 50:
        return False
    confidences = [token_index[token_id][0].confidence for token_id in token_ids]
    window_size = 50
    for i in range(0, len(confidences) - window_size + 1):
        window = confidences[i : i + window_size]
        present = sum(1 for value in window if value is not None)
        if (present / window_size) < 0.6:
            return True
    return False


def _contains_heading_line(
    token_ids: list[str],
    token_index: dict[str, tuple[OcrToken, int]],
    page_stats: dict[int, _PageStats],
) -> bool:
    group: list[OcrToken] = []
    group_page: int | None = None
    t0_y0: float | None = None
    prev: OcrToken | None = None

    for token_id in token_ids:
        entry = token_index.get(token_id)
        if entry is None:
            return False
        token, page_number = entry

        if group and page_number != group_page:
            group = []
            group_page = None
            t0_y0 = None
            prev = None

        if not _is_heading_candidate(token):
            group = []
            group_page = None
            t0_y0 = None
            prev = None
            continue

        stats = page_stats.get(page_number)
        if stats is None:
            group = []
            group_page = None
            t0_y0 = None
            prev = None
            continue

        if not group:
            group = [token]
            group_page = page_number
            t0_y0 = token.bbox.y0
            prev = token
            continue

        vertical_tol = max(3.0, 0.25 * stats.median_token_height)
        horizontal_tol = max(1.5 * stats.median_char_width, 15.0)

        if (
            t0_y0 is not None
            and prev is not None
            and abs(token.bbox.y0 - t0_y0) <= vertical_tol
            and (token.bbox.x0 - prev.bbox.x1) <= horizontal_tol
        ):
            group.append(token)
            prev = token
            if len(group) >= 2:
                return True
            continue

        group = [token]
        group_page = page_number
        t0_y0 = token.bbox.y0
        prev = token

    return False


def _is_heading_candidate(token: OcrToken) -> bool:
    return token.level == "word" and token.text.strip() != "" and token.text.isupper()


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
                if token.level != "word":
                    continue
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
