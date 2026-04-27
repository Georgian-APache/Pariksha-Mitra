# Start FastAPI with a Python that has dependencies installed.
# OneDrive often blocks pip into backend\.venv — use C:\venvs\ParikshaMitra (see guide.md).
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

$py = $null
if ($env:PARIKSHA_PYTHON -and (Test-Path $env:PARIKSHA_PYTHON)) {
  $py = $env:PARIKSHA_PYTHON
}
elseif (Test-Path "C:\venvs\ParikshaMitra\Scripts\python.exe") {
  $py = "C:\venvs\ParikshaMitra\Scripts\python.exe"
}
elseif (Test-Path ".\.venv\Scripts\python.exe") {
  $py = (Resolve-Path ".\.venv\Scripts\python.exe").Path
}
else {
  Write-Error @"
No usable Python found.

1) Create a venv outside OneDrive (recommended):
   python -m venv C:\venvs\ParikshaMitra --copies
   C:\venvs\ParikshaMitra\Scripts\python.exe -m pip install -r requirements.txt

2) Or set PARIKSHA_PYTHON to your python.exe, then re-run this script.
"@
  exit 1
}

$port = if ($env:UVICORN_PORT) { $env:UVICORN_PORT } else { "8000" }
Write-Host "Using: $py (port $port)"
Write-Host "Tip: if port 8000 is taken or returns errors, run: `$env:UVICORN_PORT='8020'; .\run-dev.ps1` and set BACKEND_DEV_PROXY_URL in frontend/.env.local to match."
& $py -m uvicorn app.main:app --reload --host 127.0.0.1 --port $port @args
