@echo off
setlocal
set "HERE=%~dp0"
set "PYW=%HERE%..\venv\Scripts\pythonw.exe"
if not exist "%PYW%" set "PYW=pythonw"
start "" "%PYW%" "%HERE%app.py"
