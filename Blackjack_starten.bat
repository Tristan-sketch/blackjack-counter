@echo off
rem Opens the blackjack counter. Double-click to run.
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv wurde nicht gefunden. Installation: https://docs.astral.sh/uv/
  pause
  exit /b 1
)
uv sync --quiet
if errorlevel 1 (
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" blackjack_counter.py
