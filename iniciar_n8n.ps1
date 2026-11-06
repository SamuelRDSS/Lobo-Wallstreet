$ErrorActionPreference = "Stop"

# Libera o node Execute Command no n8n 2.x para este ambiente local.
# Use apenas em maquina confiavel, porque esse node pode executar comandos no host.
$env:NODES_EXCLUDE = "[]"
$env:N8N_HOST = "localhost"
$env:N8N_PORT = "5678"
$env:N8N_PROTOCOL = "http"

Write-Host "Iniciando n8n em http://localhost:5678"
Write-Host "Esta janela precisa ficar aberta enquanto voce usa o n8n."
Write-Host ""

if (Get-Command n8n -ErrorAction SilentlyContinue) {
    n8n
} else {
    npx --yes n8n
}
