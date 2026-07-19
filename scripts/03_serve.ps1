# 03_serve.ps1 - run the HTTP API (Windows).
# Interactive documentation is served at http://127.0.0.1:8000/docs

$ErrorActionPreference = "Stop"

# Move to the project root (this script lives in scripts/).
Set-Location (Split-Path $PSScriptRoot -Parent)

uv run uvicorn api:app --app-dir src --host 127.0.0.1 --port 8000
