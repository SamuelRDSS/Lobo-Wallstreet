# WhatsApp Business Cloud no Lobo Walstreet

Fluxo alvo:

```text
Lobo
-> n8n
-> WhatsApp Business Cloud oficial
-> CRM
-> respostas
-> IA
```

## Envio

O front chama:

```text
POST /api/whatsapp/send
```

A API local valida o lead, monta o payload e chama:

```text
LOBO_N8N_WHATSAPP_SEND_WEBHOOK_URL
```

Valor padrão:

```text
http://localhost:5678/webhook/lobo-whatsapp/send
```

O workflow base fica em:

```text
n8n/workflow_whatsapp_business_cloud_send.json
```

No n8n, configure estas variáveis ou troque por credenciais do próprio n8n:

```text
WHATSAPP_ACCESS_TOKEN
WHATSAPP_PHONE_NUMBER_ID
WHATSAPP_GRAPH_API_URL
```

## Respostas

Quando uma resposta chegar pelo WhatsApp Business Cloud, o n8n deve enviar para:

```text
POST http://localhost:8088/api/whatsapp/inbound
```

Payload aceito:

```json
{
  "leadId": "opcional",
  "phone": "5548999999999",
  "contactName": "Nome do contato",
  "message": "Mensagem recebida",
  "token": "opcional",
  "providerPayload": {}
}
```

Se `leadId` não vier, o Lobo tenta encontrar o lead pelo telefone.

O workflow base de respostas fica em:

```text
n8n/workflow_whatsapp_business_cloud_respostas.json
```

Na produção, troque o primeiro node por um WhatsApp Trigger oficial do n8n ou conecte o webhook oficial da Meta ao n8n. Mantenha os nodes de normalização e envio para a API local.

## CRM e IA

Depois do envio, o Lobo marca o lead como:

```text
Aguardando resposta
```

Quando chega resposta, marca como:

```text
Resposta pendente
```

Também registra:

- mensagem enviada
- última resposta
- histórico de eventos
- sugestão inicial da IA

Por regra do produto, a IA **não responde automaticamente**. Ela apenas cria um rascunho em `pending_ai_reply`.

Para enviar uma resposta ao lead, o painel precisa chamar:

```text
POST /api/whatsapp/send-reply
```

Com:

```json
{
  "lead": {},
  "reply": "texto revisado pelo humano",
  "approved": true,
  "mode": "freeform"
}
```

Se `approved` não vier como `true`, o backend bloqueia o envio. Depois do envio aprovado, o CRM limpa a pendência e volta o lead para:

```text
Aguardando resposta
```

Por enquanto a IA é uma camada local simples de sugestão. A próxima etapa é trocar `backend/app/services/ai_service.py` por chamada a um modelo real, mantendo essa trava de aprovação humana antes de qualquer resposta sair pelo WhatsApp.
