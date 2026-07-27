# Bloco 1 — Prova visível (dashboard de operação + demo)

**Objetivo em uma frase:** qualquer pessoa, sem terminal, vê um ticket sintético
virar issue Jira roteada, e consegue reprocessar uma falha.

**Motivação:** critério de aprovação do bootcamp exige solução "validável por
qualquer pessoa" e "funcionando durante a apresentação". Hoje o resultado do MVP
só existe em JSON no terminal.

**Fora do escopo deste bloco:** LLM de roteamento (Bloco 2), n8n, OCR, auth do
dashboard, deploy. Dashboard é local, single-user, demo.

---

## Contrato da API — congelado

Serve de fonte única para as tasks 1.1 e 1.2, que rodam em paralelo.

### `GET /api/v1/workflows?status=<opcional>&limit=50`

```json
{
  "items": [
    {
      "workflow_execution_id": "uuid",
      "internal_correlation_id": "uuid",
      "status": "pending|processing|retry_scheduled|completed|failed|needs_human_review",
      "attempt_count": 0,
      "squad_id": "platform",
      "routing_confidence": 1.0,
      "routing_rule_version": "v1",
      "needs_human_review": false,
      "last_error": null,
      "jira_issue_key": "PLAT-123",
      "ticket": {
        "source_ticket_id": "FS-100",
        "subject": "...",
        "category": "incident",
        "priority": "high"
      },
      "updated_at": "2026-07-25T22:38:01Z"
    }
  ],
  "total": 12
}
```

`requester` NÃO entra na resposta — é PII e o dashboard não precisa dele.

### `GET /api/v1/metrics`

```json
{
  "received": 12,
  "pending": 1,
  "completed": 8,
  "retry_scheduled": 1,
  "failed": 1,
  "needs_human_review": 1,
  "duplicates_avoided": 3
}
```

`duplicates_avoided` sai de `null` se não for derivável do estado atual sem
mudança de schema. Não inventar contador.

### `POST /api/v1/workflows/{workflow_execution_id}/reprocess`

- `200` — reagendado: `{"workflow_execution_id": "...", "status": "pending", "jira_issue_key": null, "reprocessed": true, "reason": null}`
- `409` — duas causas distintas, diferenciadas pelo campo `reason`:
  - `reason: "already_linked"` — ticket já tem linha em `jira_issue_links`:
    `{"workflow_execution_id": "...", "status": "completed", "jira_issue_key": "PLAT-123", "reprocessed": false, "reason": "already_linked"}`
  - `reason: "not_eligible"` — workflow não está em `failed`/`needs_human_review` (ex.: `pending`, `processing`, `retry_scheduled`) e não tem link:
    `{"workflow_execution_id": "...", "status": "pending", "jira_issue_key": null, "reprocessed": false, "reason": "not_eligible"}`
- `404` — id inexistente

Reprocessar é idempotente. Nunca cria segunda issue Jira. O frontend deve usar
`reason` para decidir a mensagem — não deve inferir a causa a partir de
`jira_issue_key` ser `null`.

---

## Task 1.1 — endpoints de leitura e reprocessamento (backend-dev)

Critérios de aceite:

1. `GET /api/v1/workflows` retorna o payload acima, ordenado por `updated_at` desc
2. `?status=failed` filtra; status inválido retorna 422
3. `limit` tem default 50 e teto 200
4. Nenhuma resposta contém `requester`, token ou payload bruto do ticket
5. `GET /api/v1/metrics` retorna todos os campos; contador não derivável vem `null`
6. `POST .../reprocess` em execução `failed` ou `needs_human_review` reagenda e devolve 200
7. `POST .../reprocess` em ticket que já tem `jira_issue_links` devolve 409 e NÃO cria evento de outbox
8. Rodar reprocess duas vezes seguidas não gera duas issues nem dois links
9. `404` para id inexistente
10. Sem migration nova, sem mudança de schema
11. `make test` verde, incluindo os testes novos

## Task 1.2 — dashboard (frontend-dev)

Critérios de aceite:

1. Página `/` mostra os cards de métricas de `GET /api/v1/metrics`
2. Tabela de workflows com: ticket, assunto, categoria, squad, confiança,
   status, tentativas, chave Jira
3. Falhas, `retry_scheduled` e `needs_human_review` visualmente distintos
4. Botão "Reprocessar" nas linhas elegíveis, com confirmação, chamando
   `POST /api/v1/workflows/{id}/reprocess` e refletindo o resultado (inclusive 409)
5. Estado vazio explícito quando não há workflow
6. Fetch server-side (`API_URL`, default `http://localhost:8000`, `cache: 'no-store'`)
7. Zero dependência nova no `package.json`
8. `npm run build` limpo; `npm run dev` sobe sem erro
9. Nenhuma credencial, base URL corporativa ou PII renderizada

## Task 1.3 — roteiro de demo (evidence-scribe, depois de 1.1 e 1.2)

`evidence/demos/roteiro-demo.md`: sequência exata de comandos, o que narrar em
cada passo, e o print de backup. Só com dados sintéticos.
