# Contrato — Assistente (delta sobre specs/002/contracts/api-assistant.md)

O contrato de `POST /assistant/ask` de specs/002 continua valendo por inteiro (status enum, `sources[]`, guardrail de escopo, nunca bloqueia). Este arquivo cobre só o que é **novo** nesta feature: sessão persistida e contexto de chamado.

---

## Sessão — header `X-Session-Id` em toda rota do assistente

| Rota | Mudança |
|---|---|
| `POST /assistant/ask` | Passa a exigir header `X-Session-Id: <uuid>`. Sem o header, a rota **não falha** — trata como sessão nova e não persiste (degradação, não bloqueio; ver Constituição Princípio V, "limitação conhecida é documentada como decisão"). |
| `GET /assistant/conversation` | **Novo.** Mesmo header. Devolve o histórico da sessão. |

`GET /assistant/conversation`:

**200**:

```json
{
  "messages": [
    { "role": "user", "text": "Qual o status do FRESH-142?" },
    { "role": "assistant", "text": "…", "sources": [], "ticket_context": { "jira_issue_key": "FRESH-142", "status": "completed", "subject": "…", "squad_id": "SQUAD-01" } }
  ]
}
```

Sessão sem histórico (primeiro acesso) devolve `{"messages": []}`, não 404 — é o estado normal de uma conversa nova, não um erro.

**Isolamento (FR-059)**: a rota nunca aceita `session_id` por query nem body — só o header, e a busca sempre filtra por ele. Duas pessoas com headers diferentes nunca leem a mesma linha.

---

## `POST /assistant/ask` — campo aditivo na resposta

```json
{
  "status": "answered",
  "answer": "O chamado **FRESH-142** está com status *concluído* — veja mais no [Dashboard](/itsm).",
  "sources": [],
  "truncated_history": false,
  "ticket_context": {
    "jira_issue_key": "FRESH-142",
    "status": "completed",
    "subject": "Impressora sem toner — 4º andar",
    "squad_id": "SQUAD-01"
  }
}
```

`ticket_context` é `null` quando a pergunta não citou nenhuma chave Jira reconhecível, ou quando citou uma chave que não existe na base (FR-060, Edge Case correspondente — o assistente informa que não encontrou, sem inventar status; `ticket_context: null` é o sinal de que não achou).

**Regra de segurança**: `ticket_context.subject` é conteúdo externo (Princípio II) — a tela renderiza como texto simples, igual `sources[].content` já é hoje. Só o campo `answer` do próprio assistente passa pelo parser de formatação (ver research.md R5).

---

## Pipeline — passo novo entre "monta prompt" e "chama provedor"

Ordem completa (specs/002 §Pipeline + este acréscimo):

1. `ASSISTANT_ENABLED=false` ⇒ `disabled`.
2. Busca RAG, best-effort (specs/002, inalterado).
3. **Novo**: regex de chave Jira na pergunta. Achou ⇒ busca `WorkflowDetail` por `jira_issue_key`, best-effort (indisponibilidade do banco aqui **não bloqueia** — mesmo padrão do RAG). Não achou chave, ou achou mas o `SELECT` não retornou nada ⇒ segue sem `ticket_context`, sem erro.
4. Monta o prompt: trechos RAG + bloco de ticket (se houver) + histórico + pergunta, cada um em seu próprio `<untrusted_document>`.
5. Chama o provedor (inalterado).
6. Sucesso ⇒ grava pergunta + resposta em `assistant_messages` (se houver `X-Session-Id`), devolve `answered` com `ticket_context` preenchido ou `null`.

**Formatação (FR-062, FR-063)**: o `_SYSTEM_PROMPT` passa a instruir negrito/itálico via `**`/`*` e link de navegação só como `[texto](/rota)` de uma lista fechada de rotas reais anexada ao prompt — nunca URL livre, nunca HTML.
