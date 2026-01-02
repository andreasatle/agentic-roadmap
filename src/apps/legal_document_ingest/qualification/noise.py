"""Phase 3.2 noise rejection predicates."""

from __future__ import annotations

import re

from apps.legal_document_ingest.ocr.models import OcrToken


def contains_notary_block(tokens: list[OcrToken]) -> bool:
    for i, token in enumerate(tokens):
        if token.text == "NOTARY":
            return True
        if i + 1 < len(tokens) and token.text == "COUNTY" and tokens[i + 1].text == "OF":
            return True
        if i + 1 < len(tokens) and token.text == "STATE" and tokens[i + 1].text == "OF":
            return True
        if (
            i + 2 < len(tokens)
            and token.text == "SUBSCRIBED"
            and tokens[i + 1].text == "AND"
            and tokens[i + 2].text == "SWORN"
        ):
            return True
    return False


def contains_consideration_clause(tokens: list[OcrToken]) -> bool:
    for i, token in enumerate(tokens):
        if i + 1 < len(tokens) and token.text == "TEN" and tokens[i + 1].text == "DOLLARS":
            return True
        if (
            i + 2 < len(tokens)
            and token.text == "LOVE"
            and tokens[i + 1].text == "AND"
            and tokens[i + 2].text == "AFFECTION"
        ):
            return True
        if (
            i + 3 < len(tokens)
            and token.text == "OTHER"
            and tokens[i + 1].text == "GOOD"
            and tokens[i + 2].text == "AND"
            and tokens[i + 3].text == "VALUABLE"
        ):
            return True
    return False


def address_dominant(tokens: list[OcrToken]) -> bool:
    street_terms = {"STREET", "ROAD", "AVENUE"}
    zip_re = re.compile(r"^\d{5}(-\d{4})?$")
    window_size = 20
    for start in range(0, len(tokens) - window_size + 1):
        window = tokens[start : start + window_size]
        street_count = sum(1 for token in window if token.text in street_terms)
        zip_count = sum(1 for token in window if zip_re.match(token.text))
        if street_count >= 2 and zip_count >= 1:
            return True
    return False


def table_like_structure(tokens: list[OcrToken]) -> bool:
    window_size = 50
    for start in range(0, len(tokens) - window_size + 1):
        window = tokens[start : start + window_size]
        x0_map: dict[float, list[float]] = {}
        for token in window:
            bucket = round(token.bbox.x0 / 5) * 5
            x0_map.setdefault(bucket, []).append(token.bbox.y0)
        for y0s in x0_map.values():
            if len(y0s) >= 3:
                return True
    return False
