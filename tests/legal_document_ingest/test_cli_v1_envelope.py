import json
import subprocess
import sys
from pathlib import Path


PASS_PDF = Path("tests/fixtures/pass_clean_legal_description.pdf")
FAIL_PDF = Path("tests/fixtures/fail_conflicting_bearings.pdf")


def _run_cli(pdf_path: Path) -> str:
    result = subprocess.run(
        [sys.executable, "-m", "apps.legal_document_ingest.cli", str(pdf_path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def test_cli_v1_pass_envelope_shape():
    stdout = _run_cli(PASS_PDF)
    payload = json.loads(stdout)
    assert payload["status"] == "PASS"
    assert payload["final_description"] is not None
    assert payload["trace"] is not None
    assert payload["reason"] is None
    assert payload["uncertainties"] is None


def test_cli_v1_fail_envelope_shape():
    stdout = _run_cli(FAIL_PDF)
    payload = json.loads(stdout)
    assert payload["status"] == "FAIL"
    assert payload["final_description"] is None
    assert payload["trace"] is None
    assert isinstance(payload["reason"], str)
    assert payload["reason"] != ""
    assert isinstance(payload["uncertainties"], list)


def test_cli_v1_pass_determinism():
    first = _run_cli(PASS_PDF)
    second = _run_cli(PASS_PDF)
    assert first == second


def test_cli_v1_fail_determinism():
    first = _run_cli(FAIL_PDF)
    second = _run_cli(FAIL_PDF)
    assert first == second
