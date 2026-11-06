@echo off
setlocal

cd /d "%~dp0"
set PYTHONUTF8=1

powershell -ExecutionPolicy Bypass -NoProfile -File ".\iniciar_lobo.ps1"

endlocal
