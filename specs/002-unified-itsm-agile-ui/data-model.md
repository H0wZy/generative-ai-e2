# Data Model — Plataforma Unificada ITSM + Agile

**Date**: 2026-07-28 | **Plan**: [plan.md](./plan.md)

**Nenhuma migration nesta feature.** O schema PostgreSQL em `backend/app/repositories/schema.py` já contém tudo que as telas precisam. As entidades abaixo são modelos de resposta (Pydantic) e projeções — não tabelas novas.

Três origens de dado, sem sobreposição:

| Origem | Entidades | Persistência |
|---|---|---|
| PostgreSQL (existente) | Ticket, Execução de workflow, Evento de timeline, Indicador de ITSM | Fonte de verdade |
| Jira Cloud (leitura + transição) | Sprint, Item de trabalho, Épico, Coluna de board, Velocidade, Burndown | Nenhuma — lido sob demanda, cache TTL 60 s |
| SQLite + sqlite-vec (existente) | Fonte recuperada | Fonte de verdade do RAG |

---

## 1. Entidades de ITSM — projeções sobre tabelas existentes

### `WorkflowDetail` — novo modelo de resposta

Alimenta `/itsm/[id]` (FR-017). Estende `WorkflowListItem`, que já existe em `backend/app/domain/models.py`.

| Campo | Tipo | Origem |
|---|---|---|
| `workflow_execution_id` | UUID | `workflow_executions.id` |
| `internal_correlation_id` | UUID | `workflow_executions.internal_correlation_id` |
| `status` | `WorkflowStatus` | `workflow_executions.status` |
| `attempt_count` | int | `workflow_executions.attempt_count` |
| `squad_id` | str \| None | `workflow_executions.squad_id` |
| `routing_confidence` | float \| None | `workflow_executions.routing_confidence` |
| `routing_rule_version` | str \| None | `workflow_executions.routing_rule_version` |
| `routing_reason` | str \| None | `routing_decisions.reason`, decisão mais recente |
| `needs_human_review` | bool | `workflow_executions.needs_human_review` |
| `last_error` | str \| None | `workflow_executions.last_error` |
| `next_attempt_at` | datetime \| None | `workflow_executions.next_attempt_at` |
| `jira_issue_key` | str \| None | `jira_issue_links` |
| `jira_issue_url` | str \| None | Derivado de `JIRA_BASE_URL` + chave; `None` sem vínculo |
| `link_origin` | `"deterministic" \| "best_effort" \| None` | `jira_issue_links` |
| `ticket` | `TicketDetail` | `tickets` |
| `timeline` | `list[TimelineEvent]` | `audit_logs` |
| `created_at`, `updated_at` | datetime | `workflow_executions` |

**Regra**: `reprocess_eligible: bool` é derivado no servidor, não no cliente — `status in ("failed", "needs_human_review")`. Hoje essa regra está duplicada em `frontend/src/app/page.tsx` (`REPROCESS_ELIGIBLE`); ela sai do frontend e passa a vir da API, para que FR-019 e FR-020 tenham uma única definição.

### `TicketDetail`

| Campo | Tipo | Origem |
|---|---|---|
| `source_ticket_id` | str | `tickets.source_ticket_id` |
| `subject` | str | `tickets.subject` |
| `description` | str | `tickets.description` |
| `category` | str \| None | `tickets.category` |
| `priority` | str | `tickets.priority` |
| `requester` | str \| None | `tickets` |
| `source_system` | str | `tickets.source_system` |

**Regra de segurança**: `subject` e `description` são conteúdo externo não confiável (Princípio II). São renderizados como texto, nunca como HTML, e nunca entram em mensagem de erro ou log. Ao compor o prompt do assistente, passam antes por `services/redaction.py` (FR-040).

### `TimelineEvent`

Projeção de `audit_logs`, ordenada por `created_at` ascendente (FR-018).

| Campo | Tipo | Origem |
|---|---|---|
| `at` | datetime | `audit_logs.created_at` |
| `event_type` | str | `audit_logs.event_type` |
| `summary` | str | Rótulo em português derivado de `event_type` por mapa fechado |
| `detail` | dict | Subconjunto **em lista branca** de `audit_logs.details_json` |

**Regra crítica**: `details_json` **não** é devolvido inteiro. Apenas chaves de uma lista branca por `event_type` — tentativa, código de erro, chave da issue, versão da regra, duração. Um `event_type` desconhecido devolve `detail: {}`. Isso impede que conteúdo de ticket vaze pela timeline caso algum escritor de log venha a incluí-lo.

### `SlaState` — derivado, não persistido

FR-014 exige situação de SLA na lista. Não existe coluna de SLA no schema.

| Campo | Tipo | Regra |
|---|---|---|
| `available` | bool | `false` quando não há prazo conhecido |
| `minutes_left` | int \| None | Derivado de `next_attempt_at` e da política de retry |
| `tone` | `"ok" \| "warning" \| "critical" \| "unknown"` | `<60 min` crítico, `<180 min` atenção, resto ok |

**Decisão**: sem dado de prazo de SLA vindo do Freshservice, `available` é `false` e a coluna mostra `—` com rótulo "sem prazo conhecido". A alternativa — inventar um prazo — reprovaria SC-004 e mentiria numa apresentação. Registrado como limitação na seção "o que ficou de fora" do README, como o Princípio V exige.

---

## 2. Entidades de Agile — projeções sobre o Jira, sem persistência

Todas montadas por `backend/app/services/agile.py` a partir das respostas descritas em [research.md](./research.md) R1–R4.

### `BoardConfig`

De `GET /rest/agile/1.0/board/{id}/configuration`.

| Campo | Tipo | Origem |
|---|---|---|
| `board_id` | int | `id` |
| `name` | str | `name` |
| `columns` | `list[BoardColumn]` | `columnConfig.columns[]`, na ordem do board |
| `constraint_type` | `"none" \| "issueCount" \| "issueCountExclSubs"` | `columnConfig.constraintType` |
| `estimation_field_id` | str \| None | `estimation.field.fieldId`; `None` quando `type != "field"` |
| `done_status_ids` | `set[str]` | Status da **última** coluna com status mapeado |

### `BoardColumn`

| Campo | Tipo | Origem |
|---|---|---|
| `name` | str | `columns[].name` |
| `status_ids` | `list[str]` | `columns[].statuses[].id` |
| `wip_min` | int \| None | `columns[].min` |
| `wip_max` | int \| None | `columns[].max` |
| `over_wip` | bool | Derivado: `constraint_type != "none" and wip_max is not None and len(cards) > wip_max` (FR-028) |

### `Sprint`

De `GET /rest/agile/1.0/board/{id}/sprint?state=active`.

| Campo | Tipo | Regra |
|---|---|---|
| `id`, `name`, `goal` | int, str, str \| None | Diretos |
| `state` | `"active" \| "closed" \| "future"` | Direto |
| `start_date`, `end_date` | datetime \| None | Diretos |
| `days_left` | int | `max(0, (end_date - hoje).days)`; `0` sem `end_date` |
| `committed_points` | float | Soma da estimativa de todas as issues do sprint |
| `completed_points` | float | Soma da estimativa das issues em `done_status_ids` |
| `scope_added_points` | float | Pontos de issues que entraram após `start_date` (changelog do campo `Sprint`) |

Lista vazia de sprint ativo ⇒ `sprint: null` na resposta e estado vazio na tela (US3 cenário 8), não erro.

### `WorkItem`

De `/sprint/{id}/issue`, `/board/{id}/backlog` ou `/board/{id}/issue`.

| Campo | Tipo | Origem |
|---|---|---|
| `key` | str | `key` |
| `title` | str | `fields.summary` |
| `status_id`, `status_name` | str | `fields.status` |
| `column` | str \| None | Casado por `status_id` contra `BoardColumn.status_ids` |
| `points` | float \| None | `fields[estimation_field_id]`; `None` sem estimativa |
| `labels` | `list[str]` | `fields.labels` |
| `priority` | str \| None | `fields.priority.name` |
| `assignee` | `Person \| None` | `fields.assignee` |
| `epic_key`, `epic_name` | str \| None | `fields.parent` |
| `rank` | int | Posição na resposta (o endpoint já entrega ranqueado — R2) |
| `blocked_days` | int \| None | Dias no status atual, do changelog; só no dashboard |
| `blocked_reason` | str \| None | Rótulo `blocked`/`impediment` ou campo de flag |

`title` e `labels` são conteúdo externo — mesma regra de `TicketDetail`.

### `Person`

| Campo | Tipo | Regra |
|---|---|---|
| `display_name` | str | `fields.assignee.displayName` |
| `initials` | str | Derivadas do nome; fallback `"?"` |
| `avatar_url` | str \| None | **Sempre `None`** nesta feature |

**Decisão**: a URL de avatar do Jira exige autenticação. Servi-la implicaria proxy de imagem autenticado — infraestrutura que o MVP não usa. O protótipo desenha avatar como iniciais sobre cor sólida; a cor é derivada por hash estável do nome, sem imagem. Zero requisição, zero credencial no cliente.

### `Epic`

| Campo | Tipo | Regra |
|---|---|---|
| `key`, `name` | str | De `fields.parent` dos itens |
| `color` | str | Token de acento derivado por hash estável da chave |
| `total_points`, `done_points` | float | Agregados dos itens |
| `progress` | float | `done_points / total_points`; `0.0` quando total é `0` |

### `BurndownSeries`

Calculada conforme R3.

| Campo | Tipo | Regra |
|---|---|---|
| `days` | `list[date]` | De `start_date` a `end_date`, inclusive |
| `ideal` | `list[float]` | Reta de `committed_points` a `0` |
| `actual` | `list[float \| None]` | Pontos restantes por dia; `None` para dia futuro |

### `VelocityPoint`

| Campo | Tipo | Regra |
|---|---|---|
| `sprint_name` | str | Nome do sprint fechado |
| `committed`, `completed` | float | Agregados |

Últimos 5 sprints fechados, mais antigo primeiro.

### `TransitionRequest` / `TransitionResult`

FR-046, FR-047, FR-048.

| Campo | Tipo | Regra |
|---|---|---|
| `issue_key` | str | Entrada |
| `target_column` | str | Entrada — nome da coluna, não ID de status |
| `applied` | bool | Saída |
| `new_status_name` | str \| None | Status confirmado **pelo Jira**, não o otimista |
| `reason` | `"no_transition" \| "already_there" \| "forbidden" \| "unavailable" \| None` | Saída |
| `available_transitions` | `list[str]` | Nomes de status alcançáveis a partir do atual — preenchido em `no_transition` (FR-047) |

---

## 3. Entidades do Assistente

### `AssistantQuestion`

| Campo | Tipo | Regra |
|---|---|---|
| `question` | str | 1–2000 caracteres |
| `history` | `list[AssistantMessage]` | Máx. 20 turnos; truncado do mais antigo ao caber em `ASSISTANT_MAX_CONTEXT_CHARS` |

### `AssistantAnswer`

| Campo | Tipo | Regra |
|---|---|---|
| `status` | `"answered" \| "no_grounding" \| "rate_limited" \| "unavailable" \| "timeout" \| "disabled"` | Enum fechado — é o que torna FR-043 testável |
| `answer` | str \| None | `None` em todo status que não `answered` |
| `sources` | `list[RetrievedSource]` | Preenchido sempre que houve recuperação, **inclusive** quando o modelo falhou (FR-043) |
| `truncated_history` | bool | `true` quando o histórico foi cortado (FR-044) |

### `RetrievedSource`

Projeção de `SearchResult` de `rag/search/query.py`.

| Campo | Tipo | Origem |
|---|---|---|
| `file_path` | str | `SearchResult.file_path` |
| `heading_path` | str | `SearchResult.heading_path` |
| `start_line`, `end_line` | int | `SearchResult` |
| `distance` | float | `SearchResult.distance` — menor é mais similar |
| `content` | str | Trecho; **exibido como texto**, nunca interpretado (FR-045) |

### `AssistantMessage`

| Campo | Tipo | Regra |
|---|---|---|
| `role` | `"user" \| "assistant"` | Enum fechado |
| `text` | str | — |

**Persistência**: nenhuma. A conversa vive no estado do componente cliente e morre com a aba. Persistir histórico exigiria tabela, identidade de usuário e política de retenção — nada disso está no escopo.

---

## 4. Entidades do shell — só no frontend

### `Workspace`

Derivado do primeiro segmento da URL, não de estado.

| Valor | Prefixo | Seção padrão |
|---|---|---|
| `itsm` | `/itsm` | `/itsm` |
| `agile` | `/agile` | `/agile` |

`/`, `/reports`, `/assistant` e `/em-construcao/*` são compartilhados. O workspace exibido nesses casos é o último visitado, lido de `sessionStorage`, com `itsm` como padrão.

### `NavSection`

Definido em `frontend/src/lib/nav.ts`, em lista fechada (FR-003).

| Campo | Tipo |
|---|---|
| `label` | str |
| `href` | str |
| `icon` | Componente SVG inline |
| `workspace` | `"itsm" \| "agile" \| "both"` |
| `implemented` | bool — `false` aponta para `/em-construcao/[secao]` (FR-004) |

### `Indicator`

Modelo de exibição comum a Home e dashboards (FR-010 a FR-013).

| Campo | Tipo | Regra |
|---|---|---|
| `label` | str | — |
| `value` | number \| string \| None | `None` quando indisponível |
| `window` | str | Janela de tempo — obrigatória por FR-012 |
| `state` | `"ok" \| "unavailable"` | `unavailable` renderiza traço e rótulo de causa, nunca zero (FR-013) |

---

## Transições de estado

**Execução de workflow** — inalterada por esta feature. A interface apenas exibe e aciona `reprocess`:

```
pending → processing → completed
                    ↘ retry_scheduled → processing
                    ↘ failed ──────────┐ reprocess
                    ↘ needs_human_review ┘
```

**Item de trabalho** — o estado vive no Jira. A interface propõe destino; o Jira decide:

```
coluna atual ──[arraste]──> coluna destino
     │
     ├─ destino == atual   → 200 already_there, sem chamar o Jira      → card fica
     ├─ transição existe   → POST transição → status confirmado pelo Jira → card fica
     ├─ transição ausente  → 409 no_transition + available_transitions → card volta
     └─ sem permissão      → 403 forbidden                             → card volta
```

**Medido no board FRESH (2026-07-28)**: o Jira oferece transição para o status atual (`id=31 -> "Em análise"` a partir de "Em análise"). A comparação `destino == atual` é do servidor; ausência da transição na lista do Jira **não** é sinal confiável.
