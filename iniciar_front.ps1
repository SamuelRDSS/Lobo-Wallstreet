$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot
$env:PYTHONUTF8 = "1"

Write-Host "Iniciando Lobo Walstreet em http://localhost:8088/front/"
Write-Host "Esta janela precisa ficar aberta enquanto voce usa o painel."
Write-Host ""

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8088
