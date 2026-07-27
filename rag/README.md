# RAG Local

Este módulo concentrará o RAG local do MVP: ingestão incremental de Markdown, chunking, embeddings, busca semântica e exposição somente leitura por MCP.

## Limites

- Persistência: `rag/data/knowledge.db` com SQLite + sqlite-vec.
- Escopo inicial: documentos Markdown autorizados do projeto.
- Execução: local; não é uma base distribuída ou compartilhada pelo Cloud Run.
- O RAG retorna evidências e fontes; geração de resposta por LLM, quando existir, deve citar esses trechos e admitir ausência de evidência.
- O MVP não aplica timeout na busca (local, single-user, ~100 chunks). Se o RAG virar hospedado/multi-usuário, isso muda.

## Evolução OCR

OCR não integra o MVP. PDF e imagens entrarão em pipeline futuro isolado, com validação de arquivo e processamento assíncrono, antes de reutilizar o pipeline de chunking/embeddings.

Detalhes e critérios de aceite estão no [handoff RAG + MCP](../docs/handoffs/rag-mcp.md).
