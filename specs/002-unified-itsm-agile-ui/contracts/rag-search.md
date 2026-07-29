# Contrato — Serviço de busca do RAG

Processo novo, definido em `rag/http/app.py`. Consumido **apenas** pelo backend (`RAG_SEARCH_URL`), nunca pelo navegador. Não é exposto publicamente no compose.

Envolve `rag.search.query.search()` sem alterá-lo — a lógica de busca, o limiar calibrado e o fallback de cosine em Python puro continuam onde estão.

## `POST /search`

Requisição:

```json
{ "query": "idempotência do worker", "limit": 5, "max_distance": 0.50, "file_glob": null }
```

| Campo | Tipo | Padrão | Regra |
|---|---|---|---|
| `query` | str | — | Obrigatório, não vazio |
| `limit` | int | 5 | Teto 20 (`MAX_LIMIT` de `rag/search/query.py`) |
| `max_distance` | float | 0.50 | `DEFAULT_MAX_DISTANCE`, calibrado — ver research.md R5 |
| `file_glob` | str \| None | `None` | Filtro de caminho |

**200**

```json
{
  "results": [
    { "file_path": "docs/handoffs/rag-mcp.md",
      "heading_path": "Sync incremental > Chunking",
      "start_line": 88, "end_line": 112,
      "distance": 0.29,
      "content": "…" }
  ],
  "total": 1,
  "embedding_model": "all-MiniLM-L6-v2"
}
```

`results: []` com `total: 0` quando nada passa do limiar. **Não é erro** — é o caminho que leva a `no_grounding` no assistente (FR-038).

**422** — `query` vazia.

**503** — banco do RAG ausente ou não indexado. Distinto de resultado vazio: banco faltando é problema de operação, resultado vazio é resposta legítima.

## `GET /health`

`{ "status": "ok", "indexed_chunks": 412 }` — usado pelo healthcheck do compose.

## Diferenças em relação ao servidor MCP

`rag/mcp/server.py` continua existindo e inalterado. Os dois consumem a mesma função de busca; nenhum código de busca é duplicado.

| | MCP (`rag/mcp/server.py`) | HTTP (`rag/http/app.py`) |
|---|---|---|
| Transporte | stdio | HTTP |
| Consumidor | Agente de codificação | Backend da aplicação |
| `content` | Envolto em `<untrusted_document>` na origem | Trecho cru — **quem envolve é o backend**, ao montar o prompt |

**Por que o HTTP devolve cru**: o backend precisa do texto sem marcação para exibir a fonte na tela (FR-037). A marcação de não confiável é aplicada no ponto de uso — ao compor o prompt — e não no transporte.
