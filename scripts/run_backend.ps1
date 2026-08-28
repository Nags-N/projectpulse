$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    py -m venv .venv
}

& ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
Write-Host "Starting ProjectPulse backend on http://127.0.0.1:8000"
& ".venv\Scripts\python.exe" -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
