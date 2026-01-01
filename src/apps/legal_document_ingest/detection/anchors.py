from __future__ import annotations

import re
import statistics
from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict

from apps.legal_document_ingest.ocr.models import EvidenceBundle, OcrToken


class AnchorRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    page_number: int
    token_ids: list[str]
    anchor_type: str


@dataclass(frozen=True)
class _PageStats:
    median_token_height: float
    median_char_width: float


_WHITELIST = {
    "legal description": "heading:LEGAL_DESCRIPTION",
    "exhibit a": "heading:EXHIBIT_A",
    "exhibit “a”": "heading:EXHIBIT_A",
    "exhibit 'a'": "heading:EXHIBIT_A",
}
_STRIP_RE = re.compile(r"^\W+|\W+$", re.UNICODE)


def detect_anchor_candidates(
    bundle: EvidenceBundle, ordered_token_ids: list[str]
) -> list[AnchorRecord]:
    token_index, page_stats = _index_tokens(bundle)
    anchors: list[AnchorRecord] = []

    group: list[OcrToken] = []
    group_page: int | None = None
    t0_y0: float | None = None
    prev: OcrToken | None = None

    for token_id in ordered_token_ids:
        entry = token_index.get(token_id)
        if entry is None:
            raise KeyError(f"Token id not found in EvidenceBundle: {token_id}")
        token, page_number = entry

        if group and page_number != group_page:
            _flush_group(group, group_page, anchors)
            group = []
            group_page = None
            t0_y0 = None
            prev = None

        if not _is_heading_eligible(token):
            if group:
                _flush_group(group, group_page, anchors)
                group = []
                group_page = None
                t0_y0 = None
                prev = None
            continue

        stats = page_stats.get(page_number)
        if stats is None:
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
            continue

        _flush_group(group, group_page, anchors)
        group = [token]
        group_page = page_number
        t0_y0 = token.bbox.y0
        prev = token

    if group:
        _flush_group(group, group_page, anchors)

    return anchors


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


def _is_heading_eligible(token: OcrToken) -> bool:
    return (
        token.level == "word"
        and token.confidence is not None
        and token.text.strip() != ""
        and token.text.isupper()
    )


def _flush_group(
    group: list[OcrToken],
    page_number: int | None,
    anchors: list[AnchorRecord],
) -> None:
    if page_number is None or len(group) < 2:
        return
    anchor_type = _match_heading_phrase(group)
    if anchor_type is None:
        return
    anchors.append(
        AnchorRecord(
            page_number=page_number,
            token_ids=[token.token_id for token in group],
            anchor_type=anchor_type,
        )
    )


def _match_heading_phrase(tokens: list[OcrToken]) -> str | None:
    normalized = [_normalize_token_text(token.text) for token in tokens]
    phrase = " ".join(normalized)
    key = _normalize_phrase(phrase)
    return _WHITELIST.get(key)


def _normalize_token_text(text: str) -> str:
    collapsed = " ".join(text.split())
    return _STRIP_RE.sub("", collapsed)


def _normalize_phrase(text: str) -> str:
    collapsed = " ".join(text.split())
    stripped = _STRIP_RE.sub("", collapsed)
    return stripped.lower()
