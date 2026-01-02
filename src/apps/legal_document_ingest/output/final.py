from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from apps.legal_document_ingest.reconstruction.corrections import CorrectedLine
from apps.legal_document_ingest.uncertainty.gate import ExtractionContinuation


class FinalLegalDescription(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    text: str
    page_start: int
    page_end: int


def emit_final_legal_description(
    continuation: ExtractionContinuation,
    lines: list[CorrectedLine],
) -> FinalLegalDescription:
    if continuation.status != "CONTINUE":
        raise ValueError("ExtractionContinuation status is not CONTINUE.")

    texts = [line.text for line in lines]
    pages = [line.page_number for line in lines]
    text = "\n".join(texts)
    page_start = min(pages) if pages else 0
    page_end = max(pages) if pages else 0

    return FinalLegalDescription(
        text=text,
        page_start=page_start,
        page_end=page_end,
    )
