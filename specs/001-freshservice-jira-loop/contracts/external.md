# Contrato — sistemas externos consumidos

Jira contra conta sandbox real. Freshservice contra um **mock** — a conta
não teve a API key liberada pelo admin do tenant, e replicar o tenant real
do cliente é inviável (grande demais, fora do escopo). Nenhuma credencial
neste documento nem no repositório.

---

## Freshservice — leitura por polling (mock)

**Direção**: nós chamamos a API deles. Não recebemos webhook (R-003).

**Nota**: o tenant real do Freshservice nunca foi alcançado. `FreshserviceClient`
fala HTTP contra o que estiver configurado em `FRESHSERVICE_DOMAIN` — hoje
isso é um servidor mock, não o cliente. O formato abaixo é o do mock, que é
nosso e não precisa mais ser adivinhado (ver T026 e ADR em
`docs/ai/ai-decisions.md`).

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
| `squad` (campo nativo do mock) | `squad` | **A regra determinística de roteamento** (R-001) |
| `updated_at` | avanço de `sync_state.last_sync_at` | — |

O enum fechado de squad é genérico — `SQUAD-01` a `SQUAD-08` — em vez do
nome real das squads do cliente (ver D2 em `spec.md` e o ADR de decisão). O
campo `squad` do mock é lido direto, sem lista de candidatos: o formato é
nosso, não precisa ser adivinhado contra um tenant que não temos como
alcançar.

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
    "issuetype": { "name": "Tarefa" },
    "labels": [
      "freshservice-<source_ticket_id>",
      "trace-<internal_correlation_id>",
      "squad-<squad_id>"
    ]
  }
}
```

`issuetype.name` confirmado contra o sandbox real (`FRESH`): o projeto não
tem o tipo `Task`, só nomes em pt-BR (`Tarefa`, `Épico`, `Bug`, etc.) — valor
fixado em `Tarefa`, não presumido.

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
