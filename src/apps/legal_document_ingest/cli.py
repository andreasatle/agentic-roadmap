import argparse
import json
from pathlib import Path

from apps.legal_document_ingest.ocr.tesseract_adapter import TesseractAdapter
from apps.legal_document_ingest.pipeline.v1 import run_extraction_v1


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pdf_path")
    args = parser.parse_args()

    adapter = TesseractAdapter()
    bundle = adapter.run(Path(args.pdf_path))
    result = run_extraction_v1(bundle)
    if result.status == "PASS":
        envelope = {
            "status": "PASS",
            "final_description": result.final_description.model_dump(),
            "trace": result.trace.model_dump(),
            "reason": None,
            "uncertainties": None,
        }
    else:
        envelope = {
            "status": "FAIL",
            "final_description": None,
            "trace": None,
            "reason": result.reason,
            "uncertainties": [record.model_dump() for record in result.uncertainties],
        }
    pass_case = (
        envelope["final_description"] is not None
        and envelope["trace"] is not None
        and envelope["reason"] is None
        and envelope["uncertainties"] is None
    )
    fail_case = (
        envelope["final_description"] is None
        and envelope["trace"] is None
        and envelope["reason"] is not None
        and envelope["uncertainties"] is not None
    )
    if not (pass_case or fail_case):
        raise RuntimeError("Invalid contract outcome state")
    print(json.dumps(envelope))


if __name__ == "__main__":
    main()
