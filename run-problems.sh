#!/usr/bin/env bash

# This is a sanity check for running all problem types in the repo.
# It runs each problem type in sequence to ensure there are no runtime errors.

set -euo pipefail

echo "=== Running Arithmetic Problem ==="
uv run agentic-arithmetic
echo

echo "=== Running Sentiment Problem ==="
uv run agentic-sentiment
echo

echo "=== Running Coder Problem ==="
uv run agentic-coder --description "Implement a fibonacci(n) function."
echo

echo "=== Running Writer Problem ==="
uv run agentic-writer \
  --instructions "Write an article about War and Peace for the general public, informative tone, ~1000 words."
echo

echo "=== Running Document Analysis Problem ==="
uv run agentic-document \
  --tone "informative" \
  --audience "general public" \
  --goal "Outline an article about War and Peace"
echo

echo "=== All problems completed ==="
