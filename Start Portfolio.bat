@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please follow the first-time setup instructions in README.md.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" app.py --open-browser
pause
