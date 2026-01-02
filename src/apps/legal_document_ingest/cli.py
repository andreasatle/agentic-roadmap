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
    print(json.dumps(result.model_dump()))


if __name__ == "__main__":
    main()
