Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "         dearDiary Personal Semantic Diary System        " -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan

$rootDir = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $rootDir "backend"
$frontendDir = Join-Path $rootDir "frontend"

Write-Host "Starting Backend Service on http://localhost:8000 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$backendDir'; .\venv\Scripts\Activate.ps1; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

Write-Host "Starting Frontend Dev Server on http://localhost:5173 ..." -ForegroundColor Yellow
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$frontendDir'; npm run dev -- --host 0.0.0.0"

Write-Host ""
Write-Host "All services launched successfully!" -ForegroundColor Green
Write-Host "- Frontend: http://localhost:5173"
Write-Host "- Backend:  http://localhost:8000/docs"
Write-Host "========================================================" -ForegroundColor Cyan
