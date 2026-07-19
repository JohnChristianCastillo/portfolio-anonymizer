# 03_serve.ps1 - run the HTTP API and the built front end (Windows).
# Interactive API documentation is served at http://127.0.0.1:8400/docs

$ErrorActionPreference = "Stop"

# Move to the project root (this script lives in scripts/).
Set-Location (Split-Path $PSScriptRoot -Parent)

uv run uvicorn anonymizer.api:app --host 127.0.0.1 --port 8400
