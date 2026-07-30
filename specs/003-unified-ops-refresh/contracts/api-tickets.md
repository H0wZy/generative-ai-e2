# Contrato — Chamado ao vivo

Prefixo: `/api/v1`. Sem autenticação (inalterado).

**Rotas existentes reaproveitadas sem mudança de contrato**: `POST /tickets/ingest`, `POST /workflows/process-next`, `GET /workflows`, `GET /workflows/{id}`, `POST /workflows/{id}/reprocess`. A tela de criação (US1) usa as duas primeiras na sequência; nenhuma rota de ingestão nova.

---

## `PATCH /workflows/{workflow_execution_id}/ticket` — novo

FR-052. Edita campos do chamado enquanto ele não estiver concluído.

Requisição — todos os campos opcionais, só os enviados mudam:

```json
{
  "subject": "Impressora sem toner — atualizado",
  "description": "…",
  "priority": "high",
  "category": "hardware"
}
```

| Campo | Regra |
|---|---|
| `subject` | 1–255 caracteres se enviado |
| `description` | ≤ 20000 caracteres se enviado |
| `priority` | `low\|medium\|high\|urgent` se enviado |
| `category` | ≤ 80 caracteres se enviado |

**200** — `WorkflowDetail` atualizado (mesmo formato de `GET /workflows/{id}`).

**404** — workflow não encontrado.

**409** — `{"detail": "chamado já concluído"}` quando `resolved_at` não é `NULL`. Consistente com FR-052 ("enquanto ele não estiver concluído").

---

## `POST /workflows/{workflow_execution_id}/resolve` — novo

FR-053. Marca o chamado como concluído. Idempotente: chamar de novo depois de já concluído não é erro, não muda `resolved_at`.

**200**:

```json
{ "workflow_execution_id": "3f2a…", "resolved_at": "2026-07-30T14:22:00Z" }
```

`resolved_at` na resposta é sempre o do **primeiro** momento em que a ação foi aplicada — chamadas repetidas devolvem o mesmo valor (Princípio III).

**404** — workflow não encontrado.

---

## `GET /workflows` / `GET /workflows/{id}` — campo aditivo

`resolved_at: string | null` (ISO 8601) aparece em `WorkflowListItem` e `WorkflowDetail`. Ausência de valor (`null`) é o estado atual de qualquer chamado hoje na base — nenhuma migração de dado histórico marca nada como resolvido retroativamente.

---

## Fluxo da tela de criação (US1), amarrando as rotas existentes

1. `POST /tickets/ingest` com `event_id` gerado no cliente (`crypto.randomUUID()`) — garante a chave de idempotência mesmo que o usuário clique duas vezes.
2. Resposta `202` com `workflow_execution_id` → a tela já mostra o chamado na lista com status "processando" (FR-049, cenário 1).
3. `POST /workflows/process-next` chamado uma vez, imediatamente — reivindica o evento da fila (ver research.md R1 para a limitação conhecida de concorrência).
4. Tela busca `GET /workflows/{workflow_execution_id}` para mostrar o resultado (`completed` com `jira_issue_key`, ou `failed`/`retry_scheduled`/`needs_human_review` com o motivo).
