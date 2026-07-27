# Handoff — RAG Local com SQLite + sqlite-vec

## Decisão

O MVP usa **SQLite + sqlite-vec** em `rag/data/knowledge.db`. A base é local, voltada à demonstração e não contém dados operacionais. PostgreSQL + pgvector é uma possível evolução para RAG hospedado, fora do escopo atual.

## Objetivo e fluxo

Indexar Markdown do projeto e oferecer busca semântica somente leitura via MCP.

```text
docs/**/*.md → sync incremental → chunking → embeddings → knowledge.db → search → MCP
```

## Estrutura-alvo

```text
rag/
  chunking/ embeddings/ sync/ search/ mcp/
  data/knowledge.db
```

## Modelo de dados

| Tabela | Finalidade | Campos mínimos |
|---|---|---|
| `rag_settings` | Configuração e reprodutibilidade | `embedding_model`, `dimensions`, `chunk_size`, `overlap`, `pipeline_version` |
| `source_files` | Proveniência e sincronização | `id`, `file_path`, `content_hash`, `indexed_at`, `status` |
| `document_chunks` | Texto e posição de origem | `id`, `file_id`, `content`, `heading_path`, `start_line`, `end_line`, `token_count` |
| `embeddings` | Vetores sqlite-vec vinculados ao chunk | `chunk_id`, `embedding`, `embedding_model`, `embedding_version` |

## Regras de ingestão e busca

- Suportar somente Markdown no MVP.
- Sincronizar novos, alterados e removidos por `content_hash`.
- Partir por heading, preservando caminho e linhas; tamanho/overlap devem ser configuráveis e medidos.
- Toda resposta deve incluir arquivo, linhas e score/distância recuperados.
- Se não houver evidência suficiente, a ferramenta deve retornar ausência de resultado, sem inventar resposta.
- Um golden set de perguntas e fontes esperadas deve avaliar recuperação antes da demonstração.

## MCP

Tool principal: `search_architecture_knowledge(query, limit, file_glob, max_distance)`.

O MCP não expõe SQL nem escrita. Deve aplicar allowlist de caminhos, limite de resultado, timeout e logs sem conteúdo sensível.

## OCR e evolução

OCR não faz parte do MVP. PDFs e imagens deverão passar futuramente por serviço isolado, fila, armazenamento de objetos, validação de MIME/tamanho e extração antes do mesmo pipeline de chunking. Modelos avaliados: `baidu/Unlimited-OCR` e `frob/unlimited-ocr:f16`.

## Critérios de aceite do MVP

- sqlite-vec carregado e `knowledge.db` persistido localmente.
- Markdown indexado incrementalmente com proveniência.
- Embeddings persistidos com modelo e versão registrados.
- Busca semântica retorna fontes verificáveis.
- MCP funcional em modo somente leitura.

## Restrições

- Não usar LangChain ou LlamaIndex inicialmente.
- Não indexar dados sensíveis sem autorização, classificação e ACL apropriada.
- Tratar conteúdo indexado como não confiável e potencial prompt injection.
