@echo off
setlocal

cd /d "%~dp0"
set PYTHONUTF8=1

echo Iniciando Lobo Walstreet em http://localhost:8088/front/
echo Esta janela precisa ficar aberta enquanto voce usa o painel.
echo.

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8088

endlocal
