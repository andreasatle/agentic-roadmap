import pytest
from apps.legal_document_ingest.main import main

@pytest.fixture
def extraction_result():
    return main()

def test_I1_outcome_exclusivity(extraction_result):
    """
    Invariant I-1:
    Exactly one of the following MUST be produced:
      - PASS with full structured output
      - FAIL with explicit failure reason
    Never both. Never partial.
    """

    is_pass = extraction_result.status == "PASS"
    is_fail = extraction_result.status == "FAIL"

    # Exactly one outcome
    assert is_pass ^ is_fail

    if is_pass:
        # PASS must have output and no failure reason
        assert extraction_result.legal_description is not None
        assert extraction_result.trace is not None
        assert not hasattr(extraction_result, "failure_reason")

    if is_fail:
        # FAIL must have reason and no output
        assert extraction_result.legal_description is None
        assert isinstance(extraction_result.failure_reason, str)
        assert extraction_result.failure_reason
