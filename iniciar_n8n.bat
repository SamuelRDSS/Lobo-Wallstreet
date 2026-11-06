@echo off
setlocal

REM Libera o node Execute Command no n8n 2.x para este ambiente local.
REM Use apenas em maquina confiavel, porque esse node pode executar comandos no host.
set "NODES_EXCLUDE=[]"
set "N8N_HOST=localhost"
set "N8N_PORT=5678"
set "N8N_PROTOCOL=http"

echo Iniciando n8n em http://localhost:5678
echo Esta janela precisa ficar aberta enquanto voce usa o n8n.
echo.

where n8n >nul 2>nul
if %errorlevel%==0 (
  n8n
) else (
  npx --yes n8n
)

endlocal
