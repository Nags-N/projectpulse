$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (Test-Path "frontend\node_modules")) {
    Write-Host "Installing frontend dependencies..."
    Set-Location frontend
    npm install
    Set-Location $Root
}

Write-Host "Starting ProjectPulse frontend on http://127.0.0.1:5173"
Set-Location frontend
npm run dev
