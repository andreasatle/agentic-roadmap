import os

from dotenv import load_dotenv

load_dotenv(override=True)

_GENERATED_DIR = os.environ.get("AGENTIC_GENERATED_DIR") or "/opt/agentic/data/generated"


def validate_generated_dir() -> None:
    if not os.path.isdir(_GENERATED_DIR):
        raise RuntimeError(f"Generation directory does not exist: {_GENERATED_DIR}")
    if not os.access(_GENERATED_DIR, os.W_OK):
        raise RuntimeError(f"Generation directory is not writable: {_GENERATED_DIR}")
