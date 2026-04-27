# One-click local dev: backend on 8020 (avoids a stuck/broken listener on 8000) + Next.js + browser.
$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

if (-not (Test-Path "C:\venvs\ParikshaMitra\Scripts\python.exe")) {
  Write-Host "Create the venv first (outside OneDrive is best):"
  Write-Host "  python -m venv C:\venvs\ParikshaMitra --copies"
  Write-Host "  C:\venvs\ParikshaMitra\Scripts\python.exe -m pip install -r $backend\requirements.txt"
  exit 1
}

# Ensure frontend proxies to the same port we start uvicorn on.
$port = "8020"
$envBlock = @"
`$env:UVICORN_PORT = '$port'
Set-Location -LiteralPath '$backend'
.\run-dev.ps1
"@
Start-Process powershell -WorkingDirectory $backend -ArgumentList @("-NoExit", "-Command", $envBlock)

Start-Sleep -Seconds 2

Start-Process powershell -WorkingDirectory $frontend -ArgumentList @(
  "-NoExit",
  "-Command",
  "Set-Location -LiteralPath '$frontend'; npm run dev"
)

Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"

Write-Host ""
Write-Host "Opened two windows: FastAPI on http://127.0.0.1:$port and Next.js."
Write-Host "frontend/.env.local should set BACKEND_DEV_PROXY_URL=http://127.0.0.1:$port (already set by default in repo)."
Write-Host "If the site does not load, wait for 'Ready' in the Next window, then refresh the browser."
