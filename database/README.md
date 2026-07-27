# Persistência

O projeto usa duas persistências com responsabilidades separadas.

| Persistência | Escopo | Uso no MVP |
|---|---|---|
| PostgreSQL | Dados operacionais e rastreabilidade | Compartilhado pelos serviços da automação |
| SQLite + sqlite-vec | Conhecimento RAG local | Máquina/processo local de demonstração |

## PostgreSQL

Tabelas planejadas:

- `tickets`: payload normalizado, origem e estado atual; unicidade por sistema e ticket de origem.
- `squads`: catálogo de squads, backlog/projeto Jira e estado.
- `routing_decisions`: decisão, regra ou modelo/prompt usado, confiança e revisão humana.
- `workflow_executions`: estado, correlação, tentativa, erro e duração.
- `jira_issue_links`: vínculo único entre ticket e issue Jira.
- `outbox_events`: eventos persistidos para processamento assíncrono.
- `audit_logs`: ator, evento, correlação, timestamp, referência ao recurso e dados sanitizados.
- `settings`: configuração não secreta e versionada.

Auditoria e observabilidade devem ser consultáveis, com retenção, mascaramento de PII e controle de acesso definidos antes da produção.

## SQLite + sqlite-vec

O esquema RAG é definido em [`docs/handoffs/rag-mcp.md`](../docs/handoffs/rag-mcp.md). Ele não compartilha tabelas, credenciais ou ciclo de vida com PostgreSQL.

SQLite não deve ser usado como banco compartilhado por múltiplas instâncias Cloud Run. Se essa necessidade surgir, a decisão deve ser revista para uma base vetorial gerenciada, como PostgreSQL + pgvector.
