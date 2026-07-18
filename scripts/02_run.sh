#!/usr/bin/env bash
# 02_run.sh - launch the program (Linux/macOS).
# Assumes scripts/01_setup.sh has been run at least once.

set -euo pipefail

# Move to the project root (this script lives in scripts/).
cd "$(dirname "$0")/.."

# `uv run` executes inside the project environment, syncing it first if needed.
uv run python src/explore_spacy.py
