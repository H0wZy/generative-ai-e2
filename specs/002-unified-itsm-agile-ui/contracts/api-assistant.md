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
| `answered` | Recuperação e redação bem-sucedidas | Texto | Preenchido |
| `no_grounding` | Nenhum trecho abaixo de `max_distance=0.50`. **O modelo não é chamado.** | `null` | `[]` |
| `rate_limited` | Provedor devolveu `429` | `null` | **Preenchido** |
| `unavailable` | `5xx` ou erro de conexão com o provedor **ou com o serviço de busca** | `null` | Preenchido — vazio se quem falhou foi a busca |
| `timeout` | `ASSISTANT_TIMEOUT_SECONDS` expirou | `null` | **Preenchido** |
| `disabled` | `ASSISTANT_ENABLED=false` | `null` | `[]` |

**A coluna `sources` é o contrato central de FR-043**: quando a recuperação funcionou e só o modelo falhou, o usuário ainda recebe os trechos. A tela mostra as fontes e uma faixa explicando que a redação não foi produzida.

**422** — `question` vazia ou acima de 2000 caracteres.

### Regras de segurança do corpo da resposta

- `sources[].content` é conteúdo não confiável. Renderizado como texto simples; nunca como HTML, nunca como Markdown com HTML habilitado (FR-045).
- Nenhum campo carrega chave de API, nome de modelo ou URL do provedor. Erro do provedor vira `status`, nunca mensagem repassada (FR-042).
- Todo texto de ticket que componha o contexto passa por `services/redaction.py` **antes** de sair do processo (FR-040). A resposta nunca devolve o prompt enviado.

### Pipeline, na ordem

1. `ASSISTANT_ENABLED=false` ⇒ `disabled`. Sai.
2. Recupera via serviço RAG ([rag-search.md](./rag-search.md)) com `max_distance=0.50`. Serviço fora do ar ⇒ `unavailable`, **não** `no_grounding`: dizer "não há evidência na documentação" quando a busca está quebrada é afirmar algo falso sobre a base.
3. Zero trecho ⇒ `no_grounding`. **Sai sem chamar o modelo** (FR-038).
4. Monta o prompt: cada trecho envolto em `<untrusted_document>`, histórico truncado, texto de ticket redigido.
5. Chama o provedor. Falha ⇒ o `status` correspondente, com `sources` preenchido.
6. Sucesso ⇒ `answered`.

**Sem streaming**: uma requisição, uma resposta. O spec não pede resposta incremental, e streaming exigiria rota e cliente incremental (research.md R10).
