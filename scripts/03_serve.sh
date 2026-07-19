#!/usr/bin/env bash
# 03_serve.sh - run the HTTP API and the built front end (Linux/macOS).
# Interactive API documentation is served at http://127.0.0.1:8400/docs

set -euo pipefail

# Move to the project root (this script lives in scripts/).
cd "$(dirname "$0")/.."

uv run uvicorn anonymizer.api:app --host 127.0.0.1 --port 8400
