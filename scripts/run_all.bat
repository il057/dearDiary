@echo off
title dearDiary All-in-One Launcher
echo ========================================================
echo         dearDiary Personal Semantic Diary System
echo ========================================================
echo Launching Backend and Frontend in separate windows...

start "dearDiary-Backend" cmd /k "cd /d ""%~dp0..\backend"" && call venv\Scripts\activate.bat && python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

start "dearDiary-Frontend" cmd /k "cd /d ""%~dp0..\frontend"" && npm run dev -- --host 0.0.0.0"

echo.
echo Services launched!
echo - Frontend: http://localhost:5173
echo - Backend:  http://localhost:8000/docs
echo ========================================================