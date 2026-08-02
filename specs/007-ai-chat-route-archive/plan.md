# Implementation Plan: Rota por conversa e arquivamento de conversas

**Branch**: `007-ai-chat-route-archive` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-ai-chat-route-archive/spec.md`

## Summary

Duas frentes independentes que se encontram na barra lateral.

**1. Endereço por conversa.** Hoje a tela do assistente inteira mora em
`/assistant`, e a conversa aberta é query string (`?c=<id>`) ou "a mais
recente". Passa a `/ai/chat/{id}`, com `/ai/chat` sendo a conversa nova ainda
não persistida. A investigação (`research.md`) fixou duas decisões que valem
mais que o resto do plano:

- **`/ai/chat` sem segmento** para a conversa nova, em vez de um `/ai/chat/novo`
  mágico — nenhuma palavra reservada disputando espaço com identificador (R1).
- **`history.replaceState`**, não navegação de roteador, para trocar o endereço
  quando a primeira pergunta cria a conversa. É o único caminho que satisfaz
  FR-006 literalmente: navegação do App Router remontaria o componente cliente e
  abortaria o `fetch` em voo (R2). Teto anotado: seguro enquanto as duas rotas
  renderizarem o mesmo componente.

**2. Arquivar.** `assistant_conversations` ganha `archived_at TIMESTAMPTZ NULL`
(migração `008`). Coluna temporal em vez de booleana: mesmo custo, e já atende
FR-012 sem coluna extra (R3). Nenhuma rota nova — `PATCH /conversations/{id}`
ganha o campo opcional `is_archived` e `GET /conversations` ganha o filtro
`state`, com default `active` que preserva o comportamento de quem já consome.

**O prefixo `/api/v1/assistant` não muda** — o usuário tirou o rename do escopo
explicitamente. Só o endereço do navegador vira `/ai/...`.

Uma descoberta reduziu o trabalho: `get_owned()` já devolve `404` tanto para
conversa inexistente quanto para conversa de outra sessão. FR-014 e SC-006
(nenhum vazamento de existência) já estão atendidos pelo servidor atual — nada
a mudar lá, só o cliente passa a ter estado de "não encontrada" (R5).

## Technical Context

**Language/Version**: Python 3.11 (backend), TypeScript 5 / React 19 /
Next.js 16.2.11 App Router (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2 (`Mapped`/`mapped_column`),
Alembic, Pydantic v2 no backend; `@base-ui/react` (shadcn base-nova), `sonner`,
Tailwind CSS v4 no frontend. **Nenhuma dependência nova** — Constituição §V.

**Storage**: PostgreSQL. Uma coluna nova numa tabela existente
(`assistant_conversations.archived_at`), migração `008`, `down_revision = "007"`.

**Testing**: `pytest` (backend, sem rede e sem credencial — Constituição §IV),
`npx tsc --noEmit` + `npx eslint .` (frontend), e verificação manual
instrumentada por `quickstart.md`. O frontend não tem suíte automatizada; os
critérios desta spec (histórico do navegador, troca de endereço sem
recarregar) são de navegador e são verificados lá.

**Target Platform**: navegador desktop (Chromium/Firefox), tema escuro;
backend em contêiner Linux.

**Project Type**: web — `backend/` (FastAPI) + `frontend/` (Next.js).

**Performance Goals**: sem meta nova. A listagem ganha um predicado numa tabela
de dezenas de linhas por sessão.

**Constraints**: nenhuma quebra de contrato para consumidor existente (campos
novos são opcionais e o filtro tem default compatível); endereços antigos
continuam funcionando (FR-016).

**Scale/Scope**: 2 arquivos de servidor tocados + 1 migração + 1 arquivo de
teste estendido; no frontend, 2 rotas novas, 1 rota virando redirecionador, e a
barra lateral.

## Constitution Check

*GATE: passou antes da Fase 0 e revalidado após a Fase 1.*

| Princípio | Situação |
|---|---|
| **I — Determinismo primeiro, LLM como fallback** | Não se aplica: nenhuma decisão de negócio nova, nenhum caminho de LLM tocado. `POST /ask` fica intocado. |
| **II — Entrada externa é não confiável** | O identificador na URL é entrada externa: validado como UUID **antes** de virar requisição, e o servidor confirma a posse por sessão. Conversa de outra sessão devolve `404` sem corpo diferenciado — nenhuma existência vaza (FR-014). Título de conversa continua não entrando em log. |
| **III — Idempotência e rastreabilidade** | Arquivar é idempotente por construção: arquivar duas vezes preserva o `archived_at` original (data-model I-4). |
| **IV — Segredo nunca entra no repositório** | Nada de credencial nesta rodada. Testes novos são de repositório e rota — verdes sem rede e sem credencial. |
| **V — Simples agora, escalável pelas costuras** | Nenhuma dependência nova. Nenhuma rota nova no servidor (campo opcional em endpoint existente em vez de `POST /conversations/{id}/archive`). Nenhuma abstração de uma implementação só. Coluna nulável, migração reversível. Duas simplificações com teto conhecido marcadas com `ponytail:` — `history.replaceState` (R2) e ausência de índice em `archived_at` (data-model §1). A rota `/assistant` sai da navegação virando redirecionador antes de sair do disco. |

**Revalidação pós-design**: nenhuma violação. A Fase 1 removeu trabalho em vez
de adicionar (R5 dispensou mudança de servidor para FR-014/SC-006).

Pendência de processo, não de design: a Constituição §V exige a seção "o que
ficou de fora" do README atualizada a cada bloco — ela ficou devendo a rodada
006 (`T054`) e agora deve as duas. Entra nas tasks.

## Project Structure

### Documentation (this feature)

```text
specs/007-ai-chat-route-archive/
├── plan.md                      # Este arquivo
├── research.md                  # Fase 0 — R1..R7
├── data-model.md                # Fase 1 — archived_at, estados, invariantes
├── quickstart.md                # Fase 1 — verificação por critério
├── contracts/
│   ├── routes.md                # Endereços do navegador
│   └── conversations-api.md     # PATCH/GET estendidos
├── checklists/
│   └── requirements.md
└── tasks.md                     # Fase 2 (/speckit-tasks — não criado aqui)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/routes_assistant.py            # +is_archived no PATCH, +state no GET
│   └── repositories/
│       ├── schema.py                      # +archived_at em AssistantConversationRow
│       └── assistant.py                   # +set_archived, list_conversations(state)
├── migrations/versions/
│   └── 008_conversation_archived.py       # NOVO — down_revision = "007"
└── tests/
    └── test_assistant_conversation.py     # +9 testes (contracts/conversations-api.md)

frontend/
├── src/app/
│   ├── ai/chat/page.tsx                   # NOVO — conversa nova
│   ├── ai/chat/[id]/page.tsx              # NOVO — conversa existente
│   ├── ai/arquivadas/page.tsx             # NOVO — lista de arquivadas
│   └── assistant/page.tsx                 # vira redirecionador de servidor
├── src/components/assistant/
│   └── ai-assistant.tsx                   # recebe id por prop, some o ?c=
├── src/components/shell/
│   └── app-sidebar.tsx                    # links novos + ação de arquivar
└── src/lib/
    ├── nav.ts                             # /assistant → /ai/chat
    ├── use-conversations.ts               # +archive/unarchive, listagem por estado
    └── types.ts                           # +archived_at em ConversationSummary
```

**Structure Decision**: web app já estabelecido — `backend/` FastAPI e
`frontend/` Next.js App Router, ambos existentes. Nenhum diretório de topo novo.
As rotas novas ficam sob `frontend/src/app/ai/`, **fora** do grupo `(shell)`,
onde `/assistant` já vive hoje: a tela do assistente tem barra lateral própria e
essa separação não é assunto desta rodada.

## Complexity Tracking

> Preenchido só quando o Constitution Check tem violação a justificar.

Sem violação. Nada a registrar.
