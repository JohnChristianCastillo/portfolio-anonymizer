#!/usr/bin/env bash
# 03_serve.sh - run the HTTP API (Linux/macOS).
# Interactive documentation is served at http://127.0.0.1:8000/docs

set -euo pipefail

# Move to the project root (this script lives in scripts/).
cd "$(dirname "$0")/.."

uv run uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000
