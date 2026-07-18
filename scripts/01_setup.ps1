# 01_setup.ps1 - build the project environment from the lock file (Windows).
# Run once on a fresh machine before launching the program.

$ErrorActionPreference = "Stop"

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "uv is not installed. Install it first, then re-run this script:"
    Write-Host '  powershell -c "irm https://astral.sh/uv/install.ps1 | iex"'
    exit 1
}

# Move to the project root (this script lives in scripts/).
Set-Location (Split-Path $PSScriptRoot -Parent)

# Recreate the exact environment recorded in uv.lock.
uv sync

Write-Host ""
Write-Host "Environment ready. Launch the program with scripts\02_run.ps1"
