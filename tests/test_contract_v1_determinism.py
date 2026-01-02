from pathlib import Path

from apps.legal_document_ingest.ocr.tesseract_adapter import TesseractAdapter
from apps.legal_document_ingest.pipeline.v1 import run_extraction_v1


PASS_PDF = Path("tests/fixtures/pass_clean_legal_description.pdf")


def test_contract_v1_determinism():
    adapter = TesseractAdapter()
    bundle = adapter.run(PASS_PDF)

    first = run_extraction_v1(bundle)
    second = run_extraction_v1(bundle)

    first_dump = first.model_dump()
    second_dump = second.model_dump()

    assert first_dump == second_dump
    assert first.status == second.status
    assert first.final_description.model_dump() == second.final_description.model_dump()
    assert first.trace.model_dump() == second.trace.model_dump()
    assert (
        first.trace.corrections == second.trace.corrections
    )
    assert (
        first.trace.uncertainties == second.trace.uncertainties
    )
