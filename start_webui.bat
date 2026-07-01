@echo off
REM ============================================================
REM  Geração de Vídeo - IE (marketing) - start the Web UI
REM  Double-click this file, or run it from a terminal.
REM  It uses the local Python 3.12 virtual environment in .venv
REM ============================================================
cd /d "%~dp0"
REM Force UTF-8 so Windows console logging never errors on special characters
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Run the one-time setup first:
  echo     uv venv --python 3.12
  echo     uv pip install -r requirements.txt
  pause
  exit /b 1
)

echo Starting the Web UI on http://localhost:8501 ...
".venv\Scripts\python.exe" -m streamlit run "webui\App.py" --server.port=8501 --browser.gatherUsageStats=false
pause
