from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from apps.legal_document_ingest.ocr.models import EvidenceBundle, OcrToken
from apps.legal_document_ingest.reconstruction.corrections import CorrectedLine


class UncertaintyRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    type: Literal[
        "LOW_CONFIDENCE_CRITICAL_TOKEN",
        "MISSING_BEARING_SYMBOL",
        "CONFLICTING_BEARINGS",
        "UNRESOLVED_HYPHENATION",
    ]
    description: str
    token_ids: list[str]
    page_number: int


def detect_uncertainties(
    bundle: EvidenceBundle,
    lines: list[CorrectedLine],
) -> list[UncertaintyRecord]:
    token_index = _index_tokens(bundle)
    uncertainties: list[UncertaintyRecord] = []

    for line in lines:
        tokens = [_get_token(token_index, token_id) for token_id in line.token_ids]

        for token in tokens:
            if token.confidence is None and _is_critical_token(token, tokens):
                uncertainties.append(
                    UncertaintyRecord(
                        type="LOW_CONFIDENCE_CRITICAL_TOKEN",
                        description="Critical token has null confidence.",
                        token_ids=[token.token_id],
                        page_number=line.page_number,
                    )
                )

        if _has_bearing_letters(tokens) and not _has_bearing_symbols(tokens):
            uncertainties.append(
                UncertaintyRecord(
                    type="MISSING_BEARING_SYMBOL",
                    description="Bearing letters present without degree/prime symbols.",
                    token_ids=[token.token_id for token in tokens],
                    page_number=line.page_number,
                )
            )

        if _has_conflicting_bearings(tokens):
            uncertainties.append(
                UncertaintyRecord(
                    type="CONFLICTING_BEARINGS",
                    description="Conflicting bearing letters present on the same line.",
                    token_ids=[token.token_id for token in tokens],
                    page_number=line.page_number,
                )
            )

        if _has_unresolved_hyphenation(line):
            uncertainties.append(
                UncertaintyRecord(
                    type="UNRESOLVED_HYPHENATION",
                    description="Hyphenation repair applied but hyphen remains.",
                    token_ids=_hyphenation_token_ids(line),
                    page_number=line.page_number,
                )
            )

    return uncertainties


def _index_tokens(bundle: EvidenceBundle) -> dict[str, OcrToken]:
    token_index: dict[str, OcrToken] = {}
    for run in bundle.ocr_runs:
        for page in run.pages:
            for token in page.tokens:
                token_index[token.token_id] = token
    return token_index


def _get_token(token_index: dict[str, OcrToken], token_id: str) -> OcrToken:
    token = token_index.get(token_id)
    if token is None:
        raise KeyError(f"Token id not found in EvidenceBundle: {token_id}")
    return token


def _has_bearing_symbols(tokens: list[OcrToken]) -> bool:
    for token in tokens:
        if any(symbol in token.text for symbol in ("°", "º", "′", "″")):
            return True
    return False


def _has_bearing_letters(tokens: list[OcrToken]) -> bool:
    for token in tokens:
        if token.text in {"N", "S", "E", "W"}:
            return True
    return False


def _has_conflicting_bearings(tokens: list[OcrToken]) -> bool:
    has_n = any(token.text == "N" for token in tokens)
    has_s = any(token.text == "S" for token in tokens)
    has_e = any(token.text == "E" for token in tokens)
    has_w = any(token.text == "W" for token in tokens)
    return (has_n and has_s) or (has_e and has_w)


def _is_critical_token(token: OcrToken, tokens: list[OcrToken]) -> bool:
    if any(symbol in token.text for symbol in ("°", "º", "′", "″")):
        return True
    if token.text in {"N", "S", "E", "W", "THENCE"}:
        return True
    for i in range(len(tokens) - 1):
        if tokens[i].text == "BEGINNING" and tokens[i + 1].text == "AT":
            if token.token_id in {tokens[i].token_id, tokens[i + 1].token_id}:
                return True
    return False


def _has_unresolved_hyphenation(line: CorrectedLine) -> bool:
    if "-" not in line.text:
        return False
    for record in line.corrections:
        if record.type == "HYPHENATION_REPAIR":
            return True
    return False


def _hyphenation_token_ids(line: CorrectedLine) -> list[str]:
    token_ids: list[str] = []
    for record in line.corrections:
        if record.type == "HYPHENATION_REPAIR":
            token_ids.extend(record.token_ids)
    return token_ids or list(line.token_ids)
