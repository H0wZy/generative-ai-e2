# Bootcamp Gen AI E2 by TCS

Leia e mapeie primeiro os documentos-base do bootcamp para obter contexto do projeto:

- [Orientação para Projeto Final - Workshop Gen AI E2](./docs/tcs_bootcamp_e2/Orientação%20para%20Projeto%20Final%20-%20Workshop%20Gen%20AI%20E2.pdf)
- [Materiais do Bootcamp](./docs/tcs_bootcamp_e2/)

## Estrutura do Projeto

Este repositório está organizado em trilhas independentes:

- [Freshservice → Jira](./docs/handoffs/freshservice-jira.md)
- [RAG Local + MCP](./docs/handoffs/rag-mcp.md)
- [Índice de Handoffs](./docs/handoffs/README.md)

## Ordem de Leitura

1. Ler este arquivo.
2. Ler `CLAUDE.md`.
3. Ler o handoff relacionado à tarefa.
4. Inspecionar a estrutura real do repositório.
5. Implementar incrementalmente.

## Regras Gerais

- Não assumir estrutura inexistente.
- Não inventar APIs ou integrações não documentadas.
- Não adicionar segredos ao repositório.
- Validar decisões com documentação oficial quando possível.
- Preferir mudanças pequenas, testáveis e reversíveis.

## Subagents

Subagents definidos em `.claude/agents/`. O `architect` orquestra; os demais executam.

| Agente | Escopo |
|---|---|
| `architect` | Decomposição, decisões de arquitetura, revisão final |
| `backend-dev` | `backend/` — FastAPI, SQLAlchemy, worker, adaptador Jira |
| `rag-dev` | `rag/` — chunking, embeddings, busca, MCP |
| `dba` | Schema PostgreSQL e migrations Alembic |
| `devops` | Compose, Dockerfile, Makefile, n8n, CI |
| `frontend-dev` | `frontend/` — dashboard de exceções (pós-MVP) |
| `qa-dev` | Validação de critérios de aceitação com evidência |
| `cybersec` | Revisão defensiva, incluindo pipeline RAG/MCP |
| `evidence-scribe` | `evidence/`, `docs/ai/`, ADRs, fechamento de issue |

## Fonte da Verdade

Os handoffs são a principal referência técnica:

- `docs/handoffs/freshservice-jira.md`
- `docs/handoffs/rag-mcp.md`

Este arquivo não deve conter detalhes completos de implementação.
