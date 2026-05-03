# ParikshaMitra - 90 Second Demo Script

> Use this as the speaker track for a hackathon demo or screen recording. Total: ~90 seconds. Every line maps to one click.

## Pre-flight (10 seconds before recording)

1. Both servers running:
   ```powershell
   # Terminal 1
   cd backend; .\.venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --port 8000

   # Terminal 2
   cd frontend; npm run dev
   ```
2. Browser open at <http://localhost:3000>; localStorage cleared.

