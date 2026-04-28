# start.ps1 — Starts the Boundary AI backend and frontend in separate terminal windows.
# Run this from the BackendTask root directory.
# Prerequisites: Docker running, backend/.env configured, venv created, npm installed.

$root = $PSScriptRoot

Write-Host "Starting database (docker-compose)..." -ForegroundColor Cyan
docker-compose up -d db

Write-Host "Starting backend on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "Set-Location '$root\backend'; `$env:PYTHONPATH = '.'; .venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "Starting frontend on http://localhost:3000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", `
  "Set-Location '$root\frontend'; `$env:DANGEROUSLY_DISABLE_HOST_CHECK = 'true'; npm start"

Write-Host ""
Write-Host "Both servers are starting in separate windows." -ForegroundColor Green
Write-Host "  Backend:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "  Frontend: http://localhost:3000" -ForegroundColor White
