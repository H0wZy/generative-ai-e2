# Contrato — API ITSM

Prefixo: `/api/v1`. Formato: JSON. Sem autenticação nesta feature.

Rotas existentes que **não** mudam de contrato: `GET /workflows`, `GET /metrics`, `POST /workflows/{id}/reprocess`, `POST /tickets/ingest`, `POST /workflows/process-next`.

---

## `GET /workflows` — parâmetros adicionados

FR-015 e FR-016 pedem filtro combinável, busca e paginação. A rota hoje aceita apenas `status` e `limit`.

| Parâmetro | Tipo | Padrão | Regra |
|---|---|---|---|
| `status` | enum `WorkflowStatus` | — | Já existe |
| `limit` | int 1–200 | 50 | Já existe |
| `offset` | int ≥ 0 | 0 | **Novo** — paginação preservando filtros |
| `priority` | `low\|medium\|high\|urgent` | — | **Novo** |
| `squad` | str | — | **Novo** |
| `q` | str ≤ 120 | — | **Novo** — busca em `subject` e `source_ticket_id`, case-insensitive |

`WorkflowListResponse.total` passa a ser a contagem do recorte filtrado, não da página — é o número que FR-015 manda exibir.

**Compatibilidade**: todos os novos parâmetros são opcionais. Chamada existente sem eles se comporta como hoje.

---

## `GET /workflows/{workflow_execution_id}` — **novo**

Alimenta `/itsm/[id]` (FR-017, FR-018).

**200** — `WorkflowDetail`, conforme [data-model.md](../data-model.md#1-entidades-de-itsm--projeções-sobre-tabelas-existentes).

```json
{
  "workflow_execution_id": "3f2a…",
  "internal_correlation_id": "9c1b…",
  "status": "failed",
  "attempt_count": 3,
  "squad_id": "squad-pagamentos",
  "routing_confidence": 0.42,
  "routing_rule_version": "deterministic_v1",
  "routing_reason": "nenhuma categoria correspondeu",
  "needs_human_review": true,
  "last_error": "jira_unavailable",
  "next_attempt_at": null,
  "reprocess_eligible": true,
  "jira_issue_key": null,
  "jira_issue_url": null,
  "link_origin": null,
  "sla": { "available": false, "minutes_left": null, "tone": "unknown" },
  "ticket": {
    "source_ticket_id": "INC-4471",
    "subject": "…",
    "description": "…",
    "category": "acesso",
    "priority": "high",
    "requester": "…",
    "source_system": "freshservice"
  },
  "timeline": [
    { "at": "2026-07-28T10:02:11Z", "event_type": "ticket_ingested",
      "summary": "Ticket recebido", "detail": {} },
    { "at": "2026-07-28T10:02:12Z", "event_type": "routing_decided",
      "summary": "Roteamento decidido", "detail": { "rule_version": "deterministic_v1", "confidence": 0.42 } },
    { "at": "2026-07-28T10:02:40Z", "event_type": "jira_create_failed",
      "summary": "Falha ao criar issue", "detail": { "attempt": 3, "error_code": "jira_unavailable" } }
  ],
  "created_at": "…", "updated_at": "…"
}
```

**404** — `{"detail": "workflow not found"}`

**Regra de lista branca**: `timeline[].detail` só carrega chaves permitidas por `event_type`. `event_type` desconhecido ⇒ `detail: {}`. Conteúdo de ticket nunca aparece em `detail` — Princípio II.

---

## `POST /workflows/{workflow_execution_id}/reprocess` — comportamento inalterado

Já retorna `409` com `reason` em conflito. FR-020 (acionamento duplo) é atendido por esse `409` mais desabilitação do botão enquanto a requisição está em voo — nada novo no servidor.
