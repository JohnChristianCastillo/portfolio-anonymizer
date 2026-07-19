# 02_run.ps1 - launch the program (Windows).
# Assumes scripts\01_setup.ps1 has been run at least once.

$ErrorActionPreference = "Stop"

# Move to the project root (this script lives in scripts/).
Set-Location (Split-Path $PSScriptRoot -Parent)

# `uv run` executes inside the project environment, syncing it first if needed.
uv run python src/benchmark.py
