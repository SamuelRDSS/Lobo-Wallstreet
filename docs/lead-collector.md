# Lead Collector

O Lobo Walstreet agora tem uma camada de coleta automática antes do analisador.

Fluxo:

```text
provider de coleta
-> SQLite operacional
-> deduplicação
-> dados/entrada/leads_coletados.csv
-> analisador existente
-> saida/leads_priorizados.csv
-> painel e CRM
```

## Providers

Os providers ficam em:

```text
backend/app/collectors/
```

Arquivos atuais:

- `base.py`: contrato comum de provider.
- `mock_provider.py`: fonte local funcional para testar sem credenciais.
- `google_places.py`: provider preparado para Google Places com `GOOGLE_PLACES_API_KEY`.

## Deduplicação

A deduplicação acontece no SQLite usando múltiplas chaves:

- `origem + origem_id`
- telefone normalizado
- website normalizado
- `nome + endereço + cidade`

As chaves são salvas em `lead_keys`, e toda captura bruta também é registrada em `raw_leads`.

## SQLite

Banco:

```text
dados/lobo_walstreet.sqlite3
```

Tabelas:

- `leads`
- `lead_keys`
- `raw_leads`
- `analysis`
- `crm`

O CSV continua existindo para preservar o fluxo antigo e o n8n:

```text
dados/entrada/leads_coletados.csv
saida/leads_priorizados.csv
```

## API

Coletar sem analisar:

```http
POST /api/collect
```

Payload:

```json
{
  "nicho": "barbearia",
  "cidade": "São José",
  "limite": 30,
  "provider": "mock"
}
```

Coletar e analisar:

```http
POST /api/collect-and-analyze
```

Payload:

```json
{
  "nicho": "academia",
  "cidade": "Palhoça",
  "limite": 30,
  "provider": "mock",
  "preferN8n": false,
  "enrichWeb": true
}
```

Fila operacional:

```http
GET /api/pipeline
```

Retorna contagens:

- novos
- analisados
- alta prioridade
- sem telefone
- já abordados
- ignorados
- fechados

No painel, leads coletados mas ainda não analisados aparecem como `Novo` / `Não analisado`, vindos da base SQLite. Quando você roda `Buscar + analisar`, eles passam pelo analisador existente e entram no CSV priorizado.

## Google Places

Para ativar:

```text
GOOGLE_PLACES_API_KEY=sua-chave
```

Depois use:

```json
{
  "nicho": "clínica",
  "cidade": "Florianópolis",
  "limite": 30,
  "provider": "google_places"
}
```

Sem chave, use `provider: "mock"` para testar o fluxo completo sem credenciais externas.
