from pathlib import Path

from apps.legal_document_ingest.pipeline.v1 import run_extraction_v1
from apps.legal_document_ingest.ocr.tesseract_adapter import TesseractAdapter


PASS_PDF = Path("tests/fixtures/pass_clean_legal_description.pdf")
FAIL_PDF = Path("tests/fixtures/fail_conflicting_bearings.pdf")


def _run_pipeline(pdf_path: Path):
    adapter = TesseractAdapter()
    bundle = adapter.run(pdf_path)
    return run_extraction_v1(bundle)


def test_contract_v1_pass_case():
    result = _run_pipeline(PASS_PDF)
    assert result.status == "PASS"
    assert result.final_description is not None
    assert result.trace is not None
    assert result.final_description.text != ""
    assert result.trace.selected_span_token_ids
    assert result.trace.uncertainties == []


def test_contract_v1_fail_case():
    result = _run_pipeline(FAIL_PDF)
    assert result.status == "FAIL"
    assert isinstance(result.reason, str)
    assert result.reason != ""


def test_contract_v1_exclusivity():
    pass_result = _run_pipeline(PASS_PDF)
    assert getattr(pass_result, "final_description", None) is not None
    assert getattr(pass_result, "trace", None) is not None
    assert getattr(pass_result, "reason", None) is None

    fail_result = _run_pipeline(FAIL_PDF)
    assert getattr(fail_result, "final_description", None) is None
    assert getattr(fail_result, "trace", None) is None
    assert getattr(fail_result, "reason", None) is not None
