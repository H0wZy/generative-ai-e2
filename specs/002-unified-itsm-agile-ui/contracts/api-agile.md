# Contrato — API Agile

Prefixo: `/api/v1/agile`. Todas as rotas leem o Jira pelo backend — **nenhuma credencial chega ao navegador** (FR-031).

## Indisponibilidade — regra comum a todas as rotas

Quando `JIRA_*` não está configurado ou `JIRA_BOARD_ID` está ausente, toda rota responde **200** com envelope de indisponibilidade, não erro (FR-030):

```json
{ "available": false, "reason": "not_configured", "detail": "JIRA_BOARD_ID não configurado", "data": null }
```

`reason` ∈ `not_configured` | `unauthorized` | `forbidden` | `unavailable` | `rate_limited`.

Na rota de transição, `reason` acrescenta `no_transition` e `already_there`.

Resposta bem-sucedida: `{ "available": true, "reason": null, "detail": null, "data": { … } }`.

**Por que 200 e não 503**: a tela de Agile precisa renderizar o shell e um estado nomeado. Um `5xx` acionaria o `error.tsx` da rota e derrubaria a seção inteira, contrariando FR-030 e SC-008. Falha de infraestrutura real do próprio backend continua sendo `5xx`.

Cache: 60 s por chave `(rota, board_id, params)`, invalidado por transição bem-sucedida.

---

## `GET /agile/sprint`

Dashboard de Agile (FR-022, FR-023, FR-024, FR-025).

`data`:

```json
{
  "board": { "board_id": 42, "name": "SQD board" },
  "sprint": {
    "id": 118, "name": "Sprint 24", "goal": "…", "state": "active",
    "start_date": "2026-07-21T09:00:00Z", "end_date": "2026-08-01T18:00:00Z",
    "days_left": 4,
    "committed_points": 40.0, "completed_points": 22.0, "scope_added_points": 3.0
  },
  "burndown": {
    "days": ["2026-07-21", "…"],
    "ideal":  [40.0, 36.0, 32.0, "…", 0.0],
    "actual": [40.0, 39.0, 36.0, null, null]
  },
  "velocity": [
    { "sprint_name": "Sprint 21", "committed": 38.0, "completed": 31.0 },
    { "sprint_name": "Sprint 22", "committed": 40.0, "completed": 36.0 }
  ],
  "blocked": [
    { "key": "CHK-231", "title": "…", "blocked_days": 3, "blocked_reason": "aguardando fornecedor",
      "assignee": { "display_name": "…", "initials": "PN", "avatar_url": null } }
  ]
}
```

`sprint: null` quando não há sprint ativo — `available` continua `true` (US3 cenário 8). `burndown` e `blocked` vêm `null` nesse caso.

---

## `GET /agile/backlog`

FR-026. Ordem de rank vem do Jira, não é reordenada.

`data`:

```json
{
  "epics": [
    { "key": "CHK-1", "name": "Checkout Revamp", "color": "accent-600",
      "total_points": 55.0, "done_points": 22.0, "progress": 0.4 }
  ],
  "items": [
    { "rank": 1, "key": "CHK-240", "title": "…", "epic_key": "CHK-1", "epic_name": "Checkout Revamp",
      "priority": "High", "points": 5.0, "status_name": "To Do",
      "assignee": { "display_name": "…", "initials": "TR", "avatar_url": null } }
  ]
}
```

Parâmetros: `limit` (1–200, padrão 100), `offset` (≥ 0).

---

## `GET /agile/board`

FR-027, FR-028. Serve o quadro Scrum e o Kanban.

| Parâmetro | Tipo | Padrão |
|---|---|---|
| `scope` | `sprint` \| `board` | `sprint` |

`scope=sprint` (Scrum) carrega as issues do sprint ativo; `scope=board` (Kanban) carrega as issues do board.

`data`:

```json
{
  "constraint_type": "issueCount",
  "columns": [
    { "name": "To Do", "wip_min": null, "wip_max": null, "over_wip": false, "count": 6,
      "cards": [
        { "key": "CHK-240", "title": "…", "points": 5.0, "labels": ["frontend"],
          "epic_key": "CHK-1", "epic_name": "Checkout Revamp", "status_name": "To Do",
          "assignee": { "display_name": "…", "initials": "AK", "avatar_url": null } }
      ] },
    { "name": "In progress", "wip_min": 2, "wip_max": 4, "over_wip": true, "count": 5, "cards": [ … ] }
  ]
}
```

`scope=sprint` sem sprint ativo ⇒ `data: { "columns": [], "constraint_type": "none" }` com `available: true`.

---

## `POST /agile/issues/{issue_key}/transition`

FR-046, FR-047, FR-048. **Única escrita no Jira desta feature.**

Requisição:

```json
{ "target_column": "In progress" }
```

O corpo carrega **nome de coluna**, não ID de status. O mapeamento coluna→status é do servidor, que já leu a configuração do board — o navegador não precisa conhecer IDs do Jira.

**200 — aplicada**

```json
{ "applied": true, "issue_key": "CHK-231", "new_status_name": "In Progress",
  "reason": null, "available_transitions": [] }
```

`new_status_name` é o status **relido do Jira** após a transição, não o esperado. É o que SC-013 verifica.

**409 — sem transição disponível**

```json
{ "applied": false, "issue_key": "CHK-231", "new_status_name": null,
  "reason": "no_transition", "available_transitions": ["In Review", "Blocked"] }
```

`available_transitions` é o que FR-047 exige nomear.

**403 — credencial sem permissão de transição**: mesmo envelope, `reason: "forbidden"`, `available_transitions: []`.

**404** — issue inexistente. **502** — Jira indisponível, `reason: "unavailable"`.

**Sem 200 otimista**: a resposta só chega depois da confirmação do Jira. O otimismo vive no cliente, que reverte em qualquer status ≠ 200 (FR-048).

**Idempotência**: o Jira **oferece** a transição para o status atual — medido no board FRESH, `GET /transitions` de uma issue em "Em análise" devolve `id=31 -> "Em análise"`. Portanto o servidor **não pode** confiar na ausência dessa transição: compara o status atual com o destino antes de agir e, sendo iguais, devolve `200` com `applied: false` e `reason: "already_there"`, sem chamar o Jira. Nenhum estado é gravado no Postgres.
