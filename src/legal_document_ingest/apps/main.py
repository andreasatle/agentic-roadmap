# src/apps/legal_document_ingest/main.py

from typing import Any, Dict


def main() -> Dict[str, Any]:
    """
    Bootstrap-only entrypoint.

    This function intentionally does not implement any extraction logic.
    It exists solely to provide a concrete result object so that
    contract invariants can be evaluated.
    """
    return {
        "status": "FAIL",
        "legal_description": None,
        "trace": None,
        "failure_reason": "NOT_IMPLEMENTED",
    }