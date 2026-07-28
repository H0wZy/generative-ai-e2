# Contrato — sistemas externos consumidos

Duas integrações, ambas contra contas sandbox reais. Nenhuma credencial neste
documento nem no repositório.

---

## Freshservice — leitura por polling

**Direção**: nós chamamos a API deles. Não recebemos webhook (R-003).

**Autenticação**: chave de API em Basic Auth (chave como usuário, `X` como
senha, conforme a documentação do Freshservice). Origem: `.env`.

**Configuração**:

```bash
FRESHSERVICE_DOMAIN=              # ex: suaempresa.freshservice.com
FRESHSERVICE_API_KEY=             # placeholder no .env.example, valor só no .env
FRESHSERVICE_POLL_INTERVAL_SECONDS=30
```

**Chamada**: lista de tickets atualizados desde a marca de sincronização —
`GET /api/v2/tickets?updated_since={last_sync_at}`, paginado.

**Campos consumidos**:

| Campo da API | Vira | Observação |
|---|---|---|
| identificador do ticket | `source_ticket_id` | Preserva prefixo (`SR-`/`INC-`) |
| `subject` | `subject` | Entrada não confiável |
| `description` | `description` | Entrada não confiável |
| `priority` | `priority` | Mapeado para `low/medium/high/urgent` |
| `category` | `category` | Preservado, já não decide a squad |
| campo de squad | `squad` | **A regra determinística de roteamento** (R-001) |
| `updated_at` | avanço de `sync_state.last_sync_at` | — |

O nome exato do campo de squad no tenant precisa ser confirmado no sandbox
antes de F2 — pode ser campo customizado, e nesse caso vem como
`custom_fields.<nome>`. Confirmar contra o tenant, não presumir.

**Idempotência**: cada ticket lido vira um evento com a chave existente
(`source_system` + `source_ticket_id` + `event_type` + `event_id`). Um ticket
atualizado duas vezes entre polls produz um evento; reler o mesmo ticket sem
mudança produz `duplicate`, não um segundo tombamento.

**Avanço da marca**: `last_sync_at` só avança depois que a página inteira foi
persistida. Falha no meio significa reprocessar sobreposição na próxima
rodada — a idempotência absorve.

**Erros**:

| Situação | Categoria (R-007) | Efeito |
|---|---|---|
| 401 / 403 | `auth` | Poll para, registra a causa sem a credencial |
| Timeout, DNS, conexão recusada, resposta de proxy | `connectivity` | Retenta no próximo ciclo |
| 429 | `connectivity` | Respeita `Retry-After` |
| 5xx | `connectivity` | Retenta |
| Payload fora do schema | `business` | Ticket individual vai para revisão humana; os demais seguem |

---

## Jira Cloud — escrita

**Direção**: nós criamos issue. Adaptador já existe (`app/integrations/jira.py`,
REST v3, Basic Auth com e-mail + token).

**Configuração**:

```bash
JIRA_BASE_URL=
JIRA_EMAIL=
JIRA_API_TOKEN=
JIRA_PROJECT_KEY=                 # substitui JIRA_PROJECT_IDENTITY/_FINANCE/_PLATFORM
```

**Payload** — mudança em relação ao atual:

```json
{
  "fields": {
    "project": { "key": "<JIRA_PROJECT_KEY>" },
    "summary": "<assunto do chamado>",
    "description": "<ADF>",
    "issuetype": { "name": "Task" },
    "labels": [
      "freshservice-<source_ticket_id>",
      "trace-<internal_correlation_id>",
      "squad-<squad_id>"
    ]
  }
}
```

`squad-<squad_id>` é o rótulo novo (R-002). Os outros dois já existem.

O rótulo `freshservice-<source_ticket_id>` é o vínculo estruturado que FR-005
exige — o identificador do chamado deixa de depender de estar citado no título.
Rótulo do Jira não aceita espaço; `source_ticket_id` já é `LETRAS-NÚMEROS`.

**Retorno**: `201` com `key` da issue. Qualquer outro status vira
`JiraClientError`, com `retryable` verdadeiro para `{408, 429, 500, 502, 503,
504}` — comportamento atual, preservado, agora com a categoria de R-007 no
`last_error`.

**Verificação antes de criar**: o reprocessamento consulta
`jira_issue_links` pelo `ticket_id` antes de qualquer `POST`. Vínculo
existente responde `already_linked` e não toca no Jira.

---

## Dublês para teste

Nenhum teste da suíte toca a rede (FR-026).

| Externo | Dublê | Onde |
|---|---|---|
| Jira | `FakeJiraClient` — já existe, deriva a chave do `project_key` e sabe levantar `JiraClientError` sob demanda | `app/integrations/jira.py` |
| Freshservice | `respx` interceptando as rotas do poller, com fixtures de página, página vazia, 401, 429 e timeout | `tests/` |
| Ollama | `respx`, padrão já usado em `test_llm_routing.py` | `tests/` |

`make test` continua verde sem Ollama, sem credencial e sem rede.
`make routing-eval` continua exigindo Ollama e fora de `make test`.
