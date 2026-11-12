@echo off
setlocal
set "HERE=%~dp0"
set "PY=%HERE%..\venv\Scripts\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" "%HERE%app.py"
if errorlevel 1 pause
