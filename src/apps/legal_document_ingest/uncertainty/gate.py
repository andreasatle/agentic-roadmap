from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from apps.legal_document_ingest.ocr.models import EvidenceBundle, OcrToken
from apps.legal_document_ingest.reconstruction.corrections import CorrectedLine
from apps.legal_document_ingest.selection.audit import SelectionAudit
from apps.legal_document_ingest.uncertainty.detect import UncertaintyRecord


class ExtractionFailure(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    status: Literal["FAIL"]
    reason: str
    uncertainties: list[UncertaintyRecord]


class ExtractionContinuation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    status: Literal["CONTINUE"]
    uncertainties: list[UncertaintyRecord]


ExtractionGateResult = ExtractionFailure | ExtractionContinuation


def apply_failure_gate(
    bundle: EvidenceBundle,
    audit: SelectionAudit,
    lines: list[CorrectedLine],
    uncertainties: list[UncertaintyRecord],
) -> ExtractionGateResult:
    _ = audit
    _ = lines

    token_index = _index_tokens(bundle)

    for record in uncertainties:
        if record.type in {
            "CONFLICTING_BEARINGS",
            "MISSING_BEARING_SYMBOL",
            "LOW_CONFIDENCE_CRITICAL_TOKEN",
        }:
            return ExtractionFailure(
                status="FAIL",
                reason=record.type,
                uncertainties=uncertainties,
            )
        if record.type == "UNRESOLVED_HYPHENATION":
            if _hyphenation_hits_critical_tokens(record, token_index):
                return ExtractionFailure(
                    status="FAIL",
                    reason=record.type,
                    uncertainties=uncertainties,
                )

    return ExtractionContinuation(status="CONTINUE", uncertainties=uncertainties)


def _index_tokens(bundle: EvidenceBundle) -> dict[str, OcrToken]:
    token_index: dict[str, OcrToken] = {}
    for run in bundle.ocr_runs:
        for page in run.pages:
            for token in page.tokens:
                token_index[token.token_id] = token
    return token_index


def _hyphenation_hits_critical_tokens(
    record: UncertaintyRecord,
    token_index: dict[str, OcrToken],
) -> bool:
    critical_text = {"N", "S", "E", "W", "THENCE", "°", "′", "″"}
    for token_id in record.token_ids:
        token = token_index.get(token_id)
        if token is None:
            raise KeyError(f"Token id not found in EvidenceBundle: {token_id}")
        if token.text in critical_text:
            return True
    return False
