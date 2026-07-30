# Implementation Plan: Refresh Operacional — Ticket ao Vivo, Assistente Persistente, Identidade Visual

**Branch**: `003-unified-ops-refresh` | **Date**: 2026-07-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/003-unified-ops-refresh/spec.md`

## Summary

Quatro incrementos sobre a plataforma unificada existente (specs/002), todos reaproveitando pipelines já construídos em vez de criar novos:

1. Tela de criação/edição de chamado que chama o `POST /tickets/ingest` **já existente** e dispara `POST /workflows/process-next` **já existente** logo em seguida, para feedback em segundos. Só duas coisas são novas no backend: coluna `resolved_at` em `tickets` e duas rotas (`PATCH .../ticket`, `POST .../resolve`).
2. Identidade visual (paleta near-black + acento brass, trilho de status) é troca de variável CSS — o sistema `@theme inline` já existe (specs/002 research.md R9). Bug de `workspaceFor()` é uma linha.
3. Persistência de conversa do assistente: duas tabelas novas (`assistant_conversations`, `assistant_messages`), sessão sem login via id gerado no navegador.
4. Assistente ganha um segundo contexto best-effort (dado de chamado, por chave Jira citada na pergunta) seguindo o **mesmo padrão já existente** para RAG (nunca bloqueia, é best-effort, embrulhado em `<untrusted_document>`) — e o frontend passa a renderizar negrito/itálico/link em vez de texto cru.

Reports (upload de CSV/Power BI) é removido, frontend e backend, por não ter mais consumidor após a remoção da navegação.

## Technical Context

**Language/Version**: Python 3.12 (backend) · TypeScript 5 / React 19 / Next.js 16 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.0, Alembic, httpx, Pydantic v2 (backend) · Next.js App Router, Tailwind v4 `@theme inline` (frontend) — nenhuma dependência nova em nenhum dos dois lados

**Storage**: PostgreSQL (única fonte de verdade operacional, per Constituição). Uma migration Alembic nova (`tickets.resolved_at`) e duas tabelas novas (`assistant_conversations`, `assistant_messages`)

**Testing**: pytest contra Postgres real do compose, truncate entre testes (padrão já estabelecido em `backend/tests/conftest.py`) — sem mock de banco. Frontend não tem suíte automatizada hoje; validação é manual via `quickstart.md`

**Target Platform**: Docker Compose (dev/demo), navegador

**Project Type**: web application (backend/ + frontend/), estrutura já existente — sem novo projeto

**Performance Goals**: SC-001 — issue no Jira visível em <15s após criar o chamado, sem recarregar

**Constraints**: sem autenticação (limitação já documentada e mantida); sem exclusão de chamado (FR-054); modelo OpenRouter free-tier permanece single-request, sem streaming (mantido de specs/002 research.md R10)

**Scale/Scope**: escala de demo/bootcamp — um avaliador por vez, não produção multi-tenant

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Avaliação |
|---|---|
| I. Determinismo primeiro, LLM como fallback medido | PASS. Roteamento de chamado criado pela UI usa o mesmo `route_ticket()` determinístico primeiro; fallback LLM só quando squad vem vazio (comportamento já existente, inalterado). A troca de provedor do classificador (Ollama → OpenRouter) é a **única exceção real** — ver Complexity Tracking. |
| II. Entrada externa é não confiável | PASS. Dado de chamado usado como contexto do assistente é embrulhado em `<untrusted_document>` do mesmo jeito que trecho de RAG (extensão do padrão existente em `_wrap()`), passa por `redaction.py`, nunca vira instrução. |
| III. Idempotência e rastreabilidade | PASS. "Marcar como concluído" seta `resolved_at` só se estiver `NULL` — repetir a ação não gera erro nem segundo evento (FR-053). Criação de chamado pela UI reaproveita a mesma chave de idempotência já existente (`source_system`+`source_ticket_id`+`event_type`+`event_id`); o formulário gera um `event_id` novo por submissão. |
| IV. Segredo nunca entra no repositório | PASS. Nenhum segredo novo — assistente e classificador OpenRouter compartilham o mesmo `OPENROUTER_API_KEY` já existente. |
| V. Simples agora, escalável pelas costuras | PASS. Zero abstração nova de único uso: ticket criado pela UI é o mesmo `TicketIngestRequest`; conversa persistida é duas tabelas simples, sem framework de chat; formatação de resposta é parser mínimo (negrito/itálico/link), não uma dependência de Markdown completa — a superfície pedida é 3 padrões, uma lib de Markdown seria overengineering para isso. Reports sai da navegação **e** do disco (rotas/serviço/testes de `analytics`), já que nada mais os consome — não fica código morto na árvore. |

**Nenhuma violação bloqueante.** Uma exceção de infraestrutura precisa de ADR formal antes de `LLM_ENABLED=true` virar padrão com o novo provedor — registrada abaixo.

## Project Structure

### Documentation (this feature)

```text
specs/003-unified-ops-refresh/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md         # Phase 1 output
├── quickstart.md         # Phase 1 output
├── contracts/
│   ├── api-tickets.md    # PATCH/resolve novos + reuso de ingest/process-next
│   ├── api-assistant.md  # Contexto de ticket, sessão, formatação — delta sobre specs/002
│   └── ui-nav.md         # Remoção de Reports, fix workspaceFor, identidade visual
└── tasks.md              # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/
│   │   ├── routes.py              # + PATCH /workflows/{id}/ticket, POST /workflows/{id}/resolve
│   │   └── routes_assistant.py    # + sessão (header), + ticket-lookup wiring
│   ├── domain/
│   │   ├── models.py              # + resolved_at em WorkflowListItem/WorkflowDetail
│   │   └── assistant.py           # + TicketRefSource, + conversation schemas
│   ├── integrations/
│   │   └── llm.py                 # OllamaClient -> OpenRouterSquadClient (reusa openrouter.py)
│   ├── repositories/
│   │   ├── schema.py              # + AssistantConversationRow, AssistantMessageRow
│   │   └── workflows.py           # + update_ticket_fields, mark_resolved, find_by_jira_key
│   └── services/
│       ├── assistant.py           # + busca de ticket best-effort (mesmo padrão do RAG)
│       └── analytics/             # REMOVIDO (Reports)
├── migrations/versions/
│   └── 004_ticket_resolution_and_conversations.py   # novo
└── tests/
    ├── test_analytics_*.py        # REMOVIDOS (Reports)
    └── (novos testes para as rotas/serviços acima)

frontend/
├── src/
│   ├── app/
│   │   ├── itsm/new/page.tsx      # novo — formulário de criação
│   │   ├── reports/               # REMOVIDO
│   │   └── assistant/             # inalterado na rota; Chat ganha sessão
│   ├── components/
│   │   ├── itsm/                  # + ticket-form.tsx, + resolve-button.tsx
│   │   └── assistant/
│   │       ├── chat.tsx           # + sessão persistida (localStorage + fetch histórico)
│   │       └── message.tsx        # + renderer seguro (negrito/itálico/link)
│   ├── lib/
│   │   ├── nav.ts                 # remove item Reports, fix workspaceFor()
│   │   └── markdown.ts            # novo — parser mínimo, allow-list de rotas
│   └── app/globals.css            # troca de paleta (tokens, sem reescrita de componente)
```

**Structure Decision**: mantém a estrutura web app já existente (`backend/` FastAPI + `frontend/` Next.js). Nenhum diretório novo de topo — cada item novo entra na pasta que já hospeda seu tipo (rota em `api/`, tabela em `schema.py`, componente em `components/<área>/`).

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Classificador de squad muda de Ollama local para OpenRouter (API paga), contrariando "Modelos: locais por padrão" | Unificar os dois usos de LLM no mesmo provedor era pedido explícito do usuário (evitar manter Ollama rodando só para uma feature secundária, e uma única credencial/config para o time avaliar) | Manter Ollama exigiria a máquina de demonstração ter Ollama instalado e o modelo `qwen3:8b` baixado — o ambiente do avaliador (ver spec.md Assumptions, risco de Zscaler à parte) não tem isso garantido; o assistente já saiu do local por essa mesma razão (ADR-012) |

**Ação obrigatória antes de `LLM_ENABLED=true` ser o padrão**: registrar ADR-013 em `docs/ai/ai-decisions.md` (exceção formal exigida pela Governance da Constituição) e reexecutar `make routing-eval` contra o novo provedor — os números do ADR-011 (100% acurácia, 66,67% de sucesso de injeção) são do `qwen3:8b` e não se transferem. Ver [research.md](./research.md#r2).

## Constitution Check — recheck pós-design

Feito depois de `research.md`, `data-model.md` e `contracts/` prontos. Nenhum artefato de design introduziu superfície nova além da já avaliada acima: `resolved_at` é uma coluna, não uma entidade com regra própria; as duas tabelas de conversa não têm nenhuma lógica de negócio, só CRUD de histórico; o contexto de ticket no assistente reaproveita `_wrap()`/`redaction.py` ponto a ponto. **PASS, sem novas exceções.**
