@echo off
title PROJECTPULSE AI - System Launcher
echo ===========================================================================
echo  PROJECTPULSE AI - Complete System Launcher
echo ===========================================================================
echo.
echo Starting FastAPI Backend (Port 8000)...
start "ProjectPulse Backend (FastAPI)" cmd /k "cd /d "%~dp0" && .venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo Starting React Vite Frontend (Port 5173)...
start "ProjectPulse Frontend (React/Vite)" cmd /k "cd /d "%~dp0frontend" && npm run dev"

timeout /t 3 /nobreak >nul

echo.
echo ===========================================================================
echo  Services Running:
echo  - Frontend Dashboard: http://localhost:5173
echo  - Backend API Docs:   http://127.0.0.1:8000/docs
echo  - Master Demo Story:  run_demo.bat
echo ===========================================================================
echo.
start http://localhost:5173
echo Press any key to exit this launcher window (services will remain running).
pause >nul
