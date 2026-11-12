@echo off
chcp 65001 >nul
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install_SimpleCellSegmentation.ps1"
if errorlevel 1 pause
