$ErrorActionPreference = "Stop"

Set-Location $PSScriptRoot
$env:PYTHONUTF8 = "1"

function Test-LocalUrl {
    param([string]$Url)
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    } catch {
        return $false
    }
}

if (-not (Test-LocalUrl "http://localhost:5678")) {
    Write-Host "n8n nao respondeu em localhost:5678. Abrindo n8n em outra janela..."
    Start-Process powershell -WorkingDirectory (Get-Location).Path -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", ".\iniciar_n8n.ps1"
    Start-Sleep -Seconds 5
} else {
    Write-Host "n8n ja esta rodando em http://localhost:5678"
}

Write-Host "Iniciando painel/API em http://localhost:8088/front/"
Write-Host ""
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8088
