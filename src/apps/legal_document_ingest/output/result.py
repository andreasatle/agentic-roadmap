from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from apps.legal_document_ingest.ocr.models import EvidenceBundle
from apps.legal_document_ingest.scoring.heuristic import ScoredSpan
from apps.legal_document_ingest.selection.audit import SelectionAudit


class ExtractionResult(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    document_id: str
    selected_span: ScoredSpan | None
    extracted_text: str | None
    token_ids: list[str] | None
    page_start: int | None
    page_end: int | None
    failure_reason: str | None
    audit: SelectionAudit


def build_extraction_result(
    bundle: EvidenceBundle,
    audit: SelectionAudit,
) -> ExtractionResult:
    token_index = _index_tokens(bundle)
    selection = audit.selection_result
    selected = selection.selected

    if selected is None:
        return ExtractionResult(
            document_id=bundle.document_id,
            selected_span=None,
            extracted_text=None,
            token_ids=None,
            page_start=None,
            page_end=None,
            failure_reason=selection.failure_reason,
            audit=audit,
        )

    token_ids = selected.validated.span.token_ids
    texts: list[str] = []
    for token_id in token_ids:
        if token_id not in token_index:
            raise KeyError(f"Token id not found in EvidenceBundle: {token_id}")
        texts.append(token_index[token_id])

    return ExtractionResult(
        document_id=bundle.document_id,
        selected_span=selected,
        extracted_text=" ".join(texts),
        token_ids=token_ids,
        page_start=selected.validated.span.page_start,
        page_end=selected.validated.span.page_end,
        failure_reason=None,
        audit=audit,
    )


def _index_tokens(bundle: EvidenceBundle) -> dict[str, str]:
    token_index: dict[str, str] = {}
    for run in bundle.ocr_runs:
        for page in run.pages:
            for token in page.tokens:
                token_index[token.token_id] = token.text
    return token_index
