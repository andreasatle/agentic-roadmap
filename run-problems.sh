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
echo "Write a fibonacci function." | \
uv run agentic-coder
echo

echo "=== Running Writer Problem ==="
echo "Write an article about fibonacci functions." | \
uv run agentic-writer
echo

echo "=== All problems completed ==="