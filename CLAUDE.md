# Claude Code Instructions

Antes de qualquer implementação:

1. Read [AGENTS.md](/AGENTS.md)
2. Ler o handoff específico da tarefa.
3. Inspecionar a estrutura real do projeto.
4. Confirmar dependências existentes.
5. Só então propor mudanças.

## Diretrizes

- Não assumir caminhos inexistentes.
- Não alterar arquivos fora do escopo sem justificativa.
- Preferir soluções simples.
- Validar arquitetura antes de codar.
- Evitar duplicação de código.
- Não criar abstrações prematuras.

## Segurança

- Nunca commitar segredos.
- Nunca expor tokens em logs.
- Nunca assumir permissões administrativas.

## Escopos

### Automação Corporativa

Leia:

`docs/handoffs/freshservice-jira.md`

### RAG / MCP

Leia:

`docs/handoffs/rag-mcp.md`
