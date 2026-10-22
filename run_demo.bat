@echo off
title PROJECTPULSE AI - Section 57 Demonstration Story
echo ===========================================================================
echo  Starting PROJECTPULSE AI - End-to-End Demonstration Story (Section 57)
echo ===========================================================================
echo.

cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" scripts\demo_story.py
) else (
    python scripts\demo_story.py
)

echo.
echo Press any key to exit...
pause >nul
