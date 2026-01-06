import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

import yaml


_LOGGER = logging.getLogger(__name__)
# Persistence root can be overridden via AGENTIC_GENERATED_DIR.
_ROOT_DIR = os.environ.get("AGENTIC_GENERATED_DIR") or "/opt/agentic/data/generated"


def _safe_yaml_dump(intent: Any) -> str:
    if hasattr(intent, "model_dump"):
        payload = intent.model_dump()
    else:
        payload = intent
    return yaml.safe_dump(payload, sort_keys=False, default_flow_style=False)


def _atomic_write(path: str, data: bytes) -> None:
    tmp_path = f"{path}.tmp.{uuid.uuid4().hex}"
    with open(tmp_path, "wb") as handle:
        handle.write(data)
    os.replace(tmp_path, path)


def persist_generation(
    *,
    intent: Any,
    markdown: str,
    request_meta: dict[str, str | None],
) -> None:
    try:
        now = datetime.now(timezone.utc)
        timestamp = now.isoformat()
        dir_timestamp = now.strftime("%Y-%m-%dT%H-%M-%S.%f")[:-3] + "Z"
        intent_yaml = _safe_yaml_dump(intent)
        intent_bytes = intent_yaml.encode("utf-8")
        document_bytes = markdown.encode("utf-8")

        intent_sha256 = hashlib.sha256(intent_bytes).hexdigest()
        document_sha256 = hashlib.sha256(document_bytes).hexdigest()

        os.makedirs(_ROOT_DIR, exist_ok=True)
        dir_name = f"{dir_timestamp}__{uuid.uuid4().hex[:8]}"
        output_dir = os.path.join(_ROOT_DIR, dir_name)
        os.makedirs(output_dir, exist_ok=True)

        _atomic_write(os.path.join(output_dir, "intent.yaml"), intent_bytes)
        _atomic_write(os.path.join(output_dir, "document.md"), document_bytes)

        meta = {
            "timestamp_utc": timestamp,
            "intent_sha256": intent_sha256,
            "document_sha256": document_sha256,
            "request_ip": request_meta.get("request_ip"),
            "user_agent": request_meta.get("user_agent"),
        }
        _atomic_write(
            os.path.join(output_dir, "meta.json"),
            json.dumps(meta, indent=2).encode("utf-8"),
        )
        index_entry = {
            "id": dir_name,
            "timestamp_utc": timestamp,
            "intent_sha256": intent_sha256,
            "document_sha256": document_sha256,
            "request_ip": request_meta.get("request_ip"),
            "user_agent": request_meta.get("user_agent"),
        }
        try:
            index_path = os.path.join(_ROOT_DIR, "index.jsonl")
            with open(index_path, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(index_entry) + "\n")
        except Exception:
            _LOGGER.exception("Failed to append generation index")
    except Exception:
        _LOGGER.exception("Failed to persist generation")
        return
