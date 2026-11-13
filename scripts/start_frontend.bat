@echo off
title dearDiary Frontend Dev Server
echo Starting Frontend Dev Server (Vite PWA)...
cd /d "%~dp0..\frontend"
call npm run dev -- --host 0.0.0.0
pause