# Contrato — API do Assistente

Prefixo: `/api/v1/assistant`.

## `POST /assistant/ask`

FR-036 a FR-045.

Requisição:

```json
{
  "question": "Como funciona a idempotência do worker?",
  "history": [
    { "role": "user", "text": "…" },
    { "role": "assistant", "text": "…" }
  ]
}
```

| Campo | Regra |
|---|---|
| `question` | 1–2000 caracteres, obrigatório |
| `history` | Máx. 20 turnos. Truncado do mais antigo até caber em `ASSISTANT_MAX_CONTEXT_CHARS` |

**200 — sempre 200.** O resultado vive em `status`, enum fechado. É o que torna FR-043 testável: cada modo de falha tem um valor distinto, não uma string de erro variável.

```json
{
  "status": "answered",
  "answer": "O worker usa a chave source_system + source_ticket_id + …",
  "sources": [
    { "file_path": "docs/handoffs/freshservice-jira.md",
      "heading_path": "Arquitetura > Worker de outbox",
      "start_line": 120, "end_line": 148,
      "distance": 0.31,
      "content": "…" }
  ],
  "truncated_history": false
}
```

| `status` | Quando | `answer` | `sources` |
|---|---|---|---|
| `answered` | Modelo respondeu — com trecho recuperado, com conhecimento geral (FR-038), ou recusando por estar fora do escopo do projeto (FR-038a) | Texto | Preenchido se houve trecho, `[]` caso contrário |
| `rate_limited` | Provedor devolveu `429` | `null` | **Preenchido** |
| `unavailable` | `5xx` ou erro de conexão **com o provedor do modelo** | `null` | **Preenchido** |
| `timeout` | `ASSISTANT_TIMEOUT_SECONDS` expirou | `null` | **Preenchido** |
| `disabled` | `ASSISTANT_ENABLED=false` | `null` | `[]` |

**A busca do RAG nunca bloqueia a resposta (FR-038).** Zero trecho abaixo de `max_distance=0.50`, ou o serviço de busca fora do ar, seguem o mesmo caminho: o modelo é chamado do mesmo jeito, sem trecho para citar, e o prompt exige que ele deixe claro que a resposta não vem da documentação indexada. `unavailable` hoje só existe para falha do **provedor do modelo** — uma busca fora do ar não aparece no `status`, só resulta em `sources: []`.

**A coluna `sources` é o contrato central de FR-043 para as falhas do provedor**: quando a recuperação funcionou e só a chamada ao modelo falhou (`rate_limited`/`unavailable`/`timeout`), o usuário ainda recebe os trechos. A tela mostra as fontes e uma faixa explicando que a redação não foi produzida.

**422** — `question` vazia ou acima de 2000 caracteres.

### Regras de segurança do corpo da resposta

- `sources[].content` é conteúdo não confiável. Renderizado como texto simples; nunca como HTML, nunca como Markdown com HTML habilitado (FR-045).
- Nenhum campo carrega chave de API, nome de modelo ou URL do provedor. Erro do provedor vira `status`, nunca mensagem repassada (FR-042).
- Todo texto de ticket que componha o contexto passa por `services/redaction.py` **antes** de sair do processo (FR-040). A resposta nunca devolve o prompt enviado.
- O guardrail de escopo (FR-038a) e a marcação de fonte não confiável são **instrução de prompt**, não corte de código — quem impõe é o modelo, orientado pelo `_SYSTEM_PROMPT` do serviço. Uma pergunta fora de escopo ainda recebe `status: "answered"`; a recusa está no texto de `answer`.

### Pipeline, na ordem

1. `ASSISTANT_ENABLED=false` ⇒ `disabled`. Sai.
2. Tenta recuperar via serviço RAG ([rag-search.md](./rag-search.md)) com `max_distance=0.50`, best-effort: zero trecho ou serviço fora do ar ⇒ segue com `sources: []`, sem sair do pipeline.
3. Monta o prompt: cada trecho envolto em `<untrusted_document>` (se houver), histórico truncado, texto de ticket redigido.
4. Chama o provedor — sempre, mesmo sem trecho. Falha ⇒ o `status` correspondente, com `sources` preenchido (o que a busca já tinha recuperado).
5. Sucesso ⇒ `answered`, com ou sem `sources`.

**Sem streaming**: uma requisição, uma resposta. O spec não pede resposta incremental, e streaming exigiria rota e cliente incremental (research.md R10).
