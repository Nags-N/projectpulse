$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "Creating virtual environment..."
    py -m venv .venv
    & ".venv\Scripts\python.exe" -m pip install -q -r requirements.txt
}

Write-Host "Starting ProjectPulse AI tray agent..."
& ".venv\Scripts\python.exe" -m agent.main
