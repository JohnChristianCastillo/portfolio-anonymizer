#!/usr/bin/env bash
# 01_setup.sh - build the project environment from the lock file (Linux/macOS).
# Run once on a fresh machine before launching the program.

set -euo pipefail

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not installed. Install it first, then re-run this script:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  exit 1
fi

# Move to the project root (this script lives in scripts/).
cd "$(dirname "$0")/.."

# Recreate the exact environment recorded in uv.lock.
uv sync

echo ""
echo "Environment ready. Launch the program with scripts/02_run.sh"
