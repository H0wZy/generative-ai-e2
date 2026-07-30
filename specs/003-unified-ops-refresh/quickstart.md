# Quickstart: Refresh Operacional

Pré-requisitos: stack já rodando (`make dev`), `.env` do backend com `ASSISTANT_ENABLED=true`, `OPENROUTER_API_KEY` e `JIRA_*` configurados (mesmos exigidos por specs/002).

## 1. Aplicar a migration nova

```bash
make migrate
```

Confere: `tickets.resolved_at`, `assistant_conversations`, `assistant_messages` existem (`\d tickets` / `\dt` no psql).

## 2. US1 — Criar chamado e ver a issue no Jira em segundos

1. Abrir `/itsm/new`, preencher assunto + descrição + prioridade + categoria, confirmar.
2. **Esperado**: chamado aparece na lista (`/itsm`) com status "processando" imediatamente, e em poucos segundos com a chave da issue do Jira (SC-001: <15s, sem recarregar manualmente).
3. Editar o assunto do mesmo chamado ainda aberto → salvar → reabrir a tela → mudança persistida (FR-052).
4. Marcar como concluído → status muda na lista sem reload (FR-053). Clicar em "marcar como concluído" de novo não gera erro (idempotência — testar via `curl -X POST .../resolve` duas vezes, `resolved_at` igual nas duas respostas).
5. Derrubar a credencial do Jira (`.env` com token inválido) e repetir o passo 1 → tela mostra estado nomeado de falha (`failed` ou `retry_scheduled`), chamado continua visível e reprocessável.

## 3. US2 — Identidade e navegação

1. Navegar Home → ITSM → Agile → Assistente: paleta, tipografia e trilho de status idênticos nas quatro telas.
2. A partir de `/agile/backlog`, clicar em qualquer item de navegação compartilhado (ex.: Assistente de IA) → o `WorkspaceSwitcher` continua marcando "Agile" como ativo, não pula para ITSM (FR-056).
3. Sidebar não tem mais item "Reports"; acessar `/reports` diretamente devolve 404 do Next.js.

## 4. US3 — Conversa sobrevive à navegação

1. Perguntar algo ao assistente em `/assistant`.
2. Navegar para `/itsm` e voltar para `/assistant` → pergunta e resposta anteriores ainda visíveis, na ordem.
3. Fechar a aba, abrir de novo (mesmo navegador) → conversa ainda lá (via `localStorage` + `GET /assistant/conversation`).
4. Abrir em uma janela anônima (segunda "pessoa") → conversa vazia, não a mesma da primeira (FR-059 — sessões diferentes).

## 5. US4 — Assistente com dado ao vivo e formatação

1. Pegar a `jira_issue_key` de um chamado criado no passo 2. Perguntar ao assistente: "qual o status do chamado `<CHAVE>`?"
2. **Esperado**: resposta reflete o status real armazenado (FR-060), com `ticket_context` preenchido na resposta da API.
3. Perguntar por uma chave inexistente (`FAKE-999`) → assistente informa que não encontrou, sem inventar status.
4. Perguntar "onde vejo o backlog?" → resposta contém link clicável para `/agile/backlog`, sem recarregar a página (FR-063).
5. Inspecionar visualmente qualquer resposta com ênfase → negrito/itálico renderizado, nunca `**`/`*` cru (SC-006 — amostra de 20 perguntas variadas, zero marcação crua).

## 6. Golden set do classificador (gate da exceção de Constituição)

```bash
make routing-eval
```

Antes de considerar `LLM_ENABLED=true` pronto para ser o padrão: número de acurácia e de resistência a prompt injection publicado em `docs/ai/ai-decisions.md` (ADR-013), contra o novo provedor OpenRouter — não reaproveitar os números do ADR-011 (são do `qwen3:8b`).
