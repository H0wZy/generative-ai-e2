# Tasks: Tradução da prioridade exibida na fila e no detalhe de ticket

**Input**: Design documents from `/specs/011-traduzir-prioridade-fila/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: sem suíte automatizada de frontend; validação via `quickstart.md`.

**Organization**: por user story (US1 fila, US2 detalhe) — ambas dependem do módulo compartilhado, tratado como Foundational.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Foundational — módulo de tradução compartilhado

**Purpose**: única fonte de rótulo de prioridade, usada pelas duas stories.

**⚠️ CRITICAL**: bloqueia US1 e US2 — ambas consomem este módulo.

- [X] T001 Criar `frontend/src/lib/ticket-priority.ts` com `PRIORITY_LABELS` (`Record<string, string>`) e `PRIORITY_OPTIONS` (array de tuplas `[valor, rótulo]`, incluindo a opção "Todas as prioridades"), conforme `data-model.md`.
- [X] T002 Em `frontend/src/components/itsm/ticket-filters.tsx`: removido o array `PRIORITY_OPTIONS` local, importado de `lib/ticket-priority`.

**Checkpoint**: módulo pronto, filtro continua funcionando exatamente como antes (mesma fonte, origem diferente).

---

## Phase 2: User Story 1 - Prioridade em português na fila (Priority: P1) 🎯 MVP

**Goal**: badge de prioridade na tabela mostra rótulo em português.

**Independent Test**: fila com tickets de prioridades diferentes, badges mostrando "Urgente"/"Alta"/"Média"/"Baixa".

- [X] T003 [US1] Em `frontend/src/components/itsm/ticket-table.tsx`, importado `PRIORITY_LABELS` de `lib/ticket-priority`, badge troca pra `{PRIORITY_LABELS[item.ticket.priority] ?? item.ticket.priority}`.
- [X] T004 [US1] Validado: API confirma `priority` cru continua `high/low/urgent` (contrato inalterado); `PRIORITY_LABELS` cobre os 4 valores; `npm run build` compila sem erro de tipo.

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 3: User Story 2 - Prioridade em português no detalhe (Priority: P2)

**Goal**: campo "Prioridade" na tela de detalhe mostra rótulo em português.

**Independent Test**: abrir detalhe de ticket com prioridade "high", campo mostra "Alta"; formulário de edição continua funcionando com o valor original.

- [X] T005 [US2] Em `frontend/src/app/(shell)/itsm/[id]/page.tsx`, importado `PRIORITY_LABELS`, campo "Prioridade" troca pra `{PRIORITY_LABELS[detail.ticket.priority] ?? detail.ticket.priority}` — linha `priority: detail.ticket.priority as ...` do form de edição intocada. Bônus (mesmo arquivo, mesma classe de bug, específicado em specs/012 mas não coberto lá): campo "Squad" também cru (`{detail.squad_id ?? "—"}`) — corrigido reaproveitando `formatSquadLabel` de `ticket-table.tsx`.
- [X] T006 [US2] Validado: `npm run lint` e `npm run build` limpos; linha do form (`ticket-edit-panel.tsx` via prop `initialValues`) não tocada.

**Checkpoint**: US1 + US2 completas.

---

## Phase 4: Polish

- [X] T007 `npm run lint` limpo; `npm run build` compilou (16 rotas geradas).

## Dependencies & Execution Order

- Phase 1 (T001, T002) bloqueia Phase 2 e Phase 3.
- T003 (US1) e T005 (US2) são paralelos entre si (arquivos diferentes) depois da Phase 1.
- T007 roda por último.

## Parallel Example

```text
# Depois da Foundational, US1 e US2 em paralelo:
Task: "T003 [US1] badge em ticket-table.tsx"
Task: "T005 [US2] campo em itsm/[id]/page.tsx"
```

## Implementation Strategy

**MVP**: Foundational + US1 — a fila é a tela mais usada, resolve a queixa central do usuário. US2 (detalhe) é rápido de adicionar em seguida, mesmo módulo já pronto.
