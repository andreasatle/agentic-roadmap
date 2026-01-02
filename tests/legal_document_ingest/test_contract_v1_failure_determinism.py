from pathlib import Path

from apps.legal_document_ingest.ocr.tesseract_adapter import TesseractAdapter
from apps.legal_document_ingest.pipeline.v1 import run_extraction_v1


FAIL_PDF = Path("tests/fixtures/fail_conflicting_bearings.pdf")


def test_contract_v1_failure_determinism():
    adapter = TesseractAdapter()
    bundle = adapter.run(FAIL_PDF)

    first = run_extraction_v1(bundle)
    second = run_extraction_v1(bundle)

    assert first.status == "FAIL"
    assert second.status == "FAIL"
    assert first.reason == second.reason
    assert first.final_description is None
    assert second.final_description is None
    assert first.trace is None
    assert second.trace is None
    assert first.model_dump() == second.model_dump()
    assert first.reason == second.reason
