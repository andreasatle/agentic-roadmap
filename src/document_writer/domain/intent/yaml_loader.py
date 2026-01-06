"""
YAML → IntentEnvelope transpiler.

This is a thin parser only: it performs no inference, execution, or authority.
"""
from pathlib import Path
import yaml

from document_writer.domain.intent.types import IntentEnvelope


def _ensure_dict(data) -> dict:
    if not isinstance(data, dict):
        raise ValueError("Intent YAML must be a mapping at the top level.")
    return data


def load_intent_from_yaml(yaml_text: str) -> IntentEnvelope:
    """Parse YAML into an IntentEnvelope; relies on schema validation for correctness."""
    parsed = yaml.safe_load(yaml_text)
    data = _ensure_dict(parsed)
    unknown = set(data.keys()) - set(IntentEnvelope.model_fields.keys())
    if unknown:
        raise ValueError(f"Unknown intent keys: {sorted(unknown)}")
    return IntentEnvelope.model_validate(data)


def load_intent_from_file(path: str | Path) -> IntentEnvelope:
    """Load YAML from a file path and parse into an IntentEnvelope."""
    text = Path(path).read_text()
    return load_intent_from_yaml(text)
