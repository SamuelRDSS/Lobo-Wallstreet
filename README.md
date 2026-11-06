# Lobo Walstreet

Sistema local de prospecção e pré-venda automática para vender sites profissionais a pequenos negócios locais.

O projeto preserva o fluxo que já estava funcionando:

```text
coleta automática
-> SQLite operacional
-> dados/entrada/leads_coletados.csv
-> analisar_leads.py com enriquecimento
-> saida/leads_priorizados.csv
-> API local FastAPI
-> painel e CRM
```

## O que já funciona

- Leitura de CSV com leads de negócios locais.
- Coleta automática por nicho, cidade e limite.
- Provider mock local funcional e provider Google Places preparado para credencial.
- Deduplicação por telefone, website, origem/id externo e nome + endereço + cidade.
- SQLite operacional em `dados/lobo_walstreet.sqlite3`.
- Análise de presença digital: site próprio, sem site, só rede social, app Android, plataforma de agendamento, Google Sites e construtores simples.
- Enriquecimento web para procurar app Android ou evidência externa quando o CSV não traz site.
- Score de priorização e classificação de chance comercial.
- Geração de CSV principal em `saida/leads_priorizados.csv`.
- Painel web dark mode com tabela, filtros, cards de resumo, evidências, abordagem pronta e status de CRM.
- Botão `Rodar análise no n8n`, chamando `/api/analyze` e evitando CORS.
- CRM simples em `dados/crm/crm_status.json`.
- Base pronta para WhatsApp manual, WhatsApp Business Cloud oficial, histórico, respostas, IA e follow-up.

## Estrutura

```text
backend/
  app/
    main.py
    routes/
    services/
    storage/
    collectors/
    models/
    utils/
config/
  nichos.json
dados/
  entrada/
  brutos/
  crm/
  lobo_walstreet.sqlite3
docs/
  lead-collector.md
  whatsapp-business-cloud.md
front/
  index.html
n8n/
  workflow_analisador_leads.json
  workflow_webhook_analisador_leads.json
  workflow_coletor_leads.json
saida/
  leads_priorizados.csv
utils/
analisar_leads.py
iniciar_lobo.ps1
iniciar_front.ps1
iniciar_n8n.ps1
```

## Como iniciar

Na pasta do projeto:

```powershell
python -m pip install -r requirements.txt
```

As credenciais e configurações locais não devem ser commitadas. Use
`config/app.example.env` apenas como referência e configure as variáveis de
ambiente necessárias no seu computador. O `.gitignore` exclui arquivos de
ambiente locais, bancos, logs, CSVs e os dados operacionais em `dados/` e
`saida/`.

Depois:

```powershell
.\iniciar_lobo.ps1
```

Esse comando tenta abrir o n8n se ele ainda não estiver respondendo em `http://localhost:5678` e depois inicia a API/painel em:

```text
http://localhost:8088/front/
```

Se o n8n já estiver aberto, você também pode iniciar só o painel/API:

```powershell
.\iniciar_front.ps1
```

Ou pelo Prompt de Comando:

```cmd
iniciar_front.bat
```

O comando antigo `python front_server.py` continua funcionando, mas agora ele sobe a mesma API FastAPI.

## Deploy na Vercel

O entrypoint FastAPI está configurado em `pyproject.toml`. Na Vercel, os dados
de execução (SQLite, CRM, CSVs e leads coletados) ficam em `/tmp/lobo-walstreet`,
pois o diretório do código é somente leitura. Esse armazenamento é temporário e
pode ser apagado entre execuções; para persistir dados em produção, configure
um banco e armazenamento externos.

## n8n

Use o workflow:

```text
n8n/workflow_webhook_analisador_leads.json
```

Para disparar coleta + análise pelo n8n, use:

```text
n8n/workflow_coletor_leads.json
```

Webhook esperado pela API:

```text
http://localhost:5678/webhook/lead-site-analyzer-webhook/webhook-csv/analisar-leads-sites
```

Payload enviado pela API:

```json
{
  "csvPath": "C:\\CAMINHO\\DO\\PROJETO\\dados\\entrada\\google_places_barbearias_sao_jose.csv",
  "outputDir": "C:\\CAMINHO\\DO\\PROJETO\\saida",
  "enrichWeb": true
}
```

No n8n 2.x, o node `Execute Command` pode vir bloqueado. Os scripts `iniciar_n8n.ps1` e `iniciar_n8n.bat` definem `NODES_EXCLUDE=[]` para liberar esse node no seu ambiente local.

## Rodar análise sem n8n

Para testar o analisador direto:

```powershell
python .\analisar_leads.py --input .\dados\entrada\google_places_barbearias_sao_jose.csv --output-dir .\saida --pretty --enrich-web
```

## API local

Principais endpoints:

- `GET /api/health`: mostra status básico e webhook configurado.
- `GET /api/leads`: lê `saida/leads_priorizados.csv`, aplica CRM e devolve JSON para o painel.
- `GET /api/pipeline`: mostra a fila operacional do SQLite.
- `POST /api/collect`: busca leads, salva brutos, deduplica e exporta `dados/entrada/leads_coletados.csv`.
- `POST /api/collect-and-analyze`: busca, deduplica, roda análise e atualiza `saida/leads_priorizados.csv`.
- `POST /api/analyze`: chama o webhook do n8n por padrão.
- `POST /api/message`: gera a mensagem comercial para um lead.
- `GET /api/crm/statuses`: lista status comerciais.
- `POST /api/crm`: salva status e notas em `dados/crm/crm_status.json`.
- `POST /api/whatsapp/send`: envia o lead para o webhook de WhatsApp do n8n.
- `POST /api/whatsapp/inbound`: recebe resposta do n8n, atualiza CRM e gera sugestão da IA.
- `POST /api/whatsapp/send-reply`: envia uma resposta revisada, somente com confirmação humana.
- `POST /api/ai/draft-reply`: gera uma sugestão local de resposta.

## Lead Collector

O Lobo agora também funciona como coletor.

Payload de coleta:

```json
{
  "nicho": "barbearia",
  "cidade": "São José",
  "limite": 30,
  "provider": "mock"
}
```

Payload para coletar e analisar:

```json
{
  "nicho": "clínica",
  "cidade": "Florianópolis",
  "limite": 30,
  "provider": "mock",
  "preferN8n": false,
  "enrichWeb": true
}
```

Providers atuais:

- `mock`: coleta local sem credenciais, boa para testar o fluxo inteiro.
- `google_places`: preparado para usar `GOOGLE_PLACES_API_KEY`.

Documentação detalhada:

```text
docs/lead-collector.md
```

## WhatsApp Business Cloud

Fluxo preparado:

```text
Lobo
-> n8n
-> WhatsApp Business Cloud oficial
-> CRM
-> respostas
-> IA
```

Arquivos principais:

- `n8n/workflow_whatsapp_business_cloud_send.json`: recebe envio do Lobo e chama a Cloud API.
- `n8n/workflow_whatsapp_business_cloud_respostas.json`: normaliza resposta e devolve para o CRM/IA do Lobo.
- `docs/whatsapp-business-cloud.md`: contrato completo de payloads e configuração.

Variáveis úteis:

```text
LOBO_N8N_WHATSAPP_SEND_WEBHOOK_URL=http://localhost:5678/webhook/lobo-whatsapp/send
LOBO_WHATSAPP_INBOUND_TOKEN=troque-por-um-token-local
WHATSAPP_ACCESS_TOKEN=token-da-meta-no-n8n
WHATSAPP_PHONE_NUMBER_ID=id-do-numero-na-meta
```

O botão `Enviar via n8n` já aparece no painel. Sem credenciais da Meta configuradas no n8n, ele deve falhar com erro de webhook/Cloud API. Depois das credenciais, ele passa a registrar o lead como `Aguardando resposta`.

Quando o lead responde, a IA apenas cria um rascunho. O CRM marca como `Resposta pendente`, e o painel só envia se alguém clicar em `Confirmar e enviar resposta`. O backend também exige `approved=true`, então a trava não depende apenas do front.

## CSV de entrada

O arquivo antigo continua existindo:

```text
dados/entrada/google_places_barbearias_sao_jose.csv
```

O arquivo operacional gerado pelo coletor e usado pelo novo fluxo fica em:

```text
dados/entrada/leads_coletados.csv
```

O sistema é resiliente a colunas faltantes. Campos úteis:

- `nome`
- `categoria`
- `cidade`
- `telefone`
- `website`
- `instagram`
- `endereco`
- `nota`
- `avaliacoes`

## Saída

O arquivo principal do produto é:

```text
saida/leads_priorizados.csv
```

Campos importantes gerados:

- `score`
- `chance`
- `presenca_digital`
- `url_detectada`
- `fonte_detectada`
- `titulo_detectado`
- `status_enriquecimento`
- `motivo`
- `mensagem_whatsapp`
- `whatsapp_url`

## Mensagens comerciais

O backend gera abordagens por cenário:

- Tem site: sugere melhoria de conversão e apresentação.
- Sem site: mostra oportunidade perdida no Google.
- Só rede social: posiciona o site como central de confiança.
- App Android encontrado: elogia maturidade digital e propõe site como vitrine central.
- Plataforma de agendamento: mantém a agenda atual e propõe site como camada comercial.

## CRM simples

Status disponíveis:

- Não abordado
- Pronto para envio
- Abordado
- Aguardando resposta
- Respondeu
- Resposta pendente
- Interessado
- Fechado
- Sem interesse

O CRM ainda preserva o JSON local para compatibilidade, mas também sincroniza status e eventos no SQLite operacional.

## Próximas fases

- Aprovar templates da primeira mensagem na Meta.
- Trocar a sugestão local de IA por modelo real.
- IA classificando respostas dentro da janela de atendimento.
- Follow-up automático.
- Histórico por lead.
- CRM com funil, tarefas e datas.
- Geração de mensagens com IA usando contexto do nicho e evidências encontradas.

## Observação

O produto já está funcional localmente. O botão de WhatsApp automático agora existe, mas depende das credenciais oficiais da Meta configuradas no n8n para enviar de verdade.
