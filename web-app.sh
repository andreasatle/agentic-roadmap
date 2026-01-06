#!/usr/bin/env bash
set -e

# Load environment variables (ADMIN_PASSWORD, AGENTIC_GENERATED_DIR, etc.)
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi

# Fallbacks (safe defaults for local dev)
# export AGENTIC_GENERATED_DIR="${AGENTIC_GENERATED_DIR:-./generated}"
# export ADMIN_PASSWORD="${ADMIN_PASSWORD:-admin}"

# mkdir -p "$AGENTIC_GENERATED_DIR"

# Run FastAPI app
uv run uvicorn web.api:app \
  --host 127.0.0.1 \
  --port 8000 \
  --reload
