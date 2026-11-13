@echo off
title dearDiary Backend Service
echo Starting Backend Service (FastAPI + LanceDB)...
cd /d "%~dp0..\backend"
call "%~dp0..\backend\venv\Scripts\activate.bat"
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause