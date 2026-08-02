---

description: "Task list for feature 008 — Localização PT-BR completa do frontend"

---

# Tasks: Localização PT-BR completa do frontend

**Input**: Design documents from `/specs/008-localizacao-ptbr-frontend/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [quickstart.md](./quickstart.md)

**Tests**: sem suíte automatizada de frontend no projeto (plan.md → Technical
Context). Validação é estática (`tsc`, `eslint`, `next build`) e manual
(quickstart.md) — nenhuma tarefa de teste automatizado é gerada.

**Status**: todas as tarefas abaixo já foram executadas na sessão que gerou
este plano (auditoria de código seguida de implementação imediata, dado o
escopo pequeno e o risco baixo). Marcadas `[x]` para refletir o estado real;
este arquivo documenta o que foi feito, na ordem em que teria sido feito,
para rastreabilidade — não é um roteiro pendente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: podia rodar em paralelo (arquivo diferente, sem dependência)
- **[Story]**: a qual user story do spec.md a tarefa pertence
- Caminhos de arquivo são relativos a `frontend/src/`

## Path Conventions

Web app com `frontend/` (Next.js) — todos os caminhos abaixo são relativos a
`frontend/src/`, conforme `plan.md` → Project Structure.

---

## Phase 1: Setup

**Purpose**: confirmar baseline antes de qualquer mudança

- [x] T001 Confirmar baseline limpa: `npx tsc --noEmit`, `npx eslint src`,
      `npm run build` sem erro em `frontend/` (linha de partida antes da
      tradução)

---

## Phase 2: Foundational

**Purpose**: pré-requisito bloqueante compartilhado por todas as user stories

Nenhuma tarefa fundacional nova: a feature reaproveita 100% da estrutura de
navegação (`NAV`, componentes shadcn) já existente das rodadas 004-007 (ver
`plan.md` → Constitution Check, Principle V). Nenhum item bloqueia o início
das user stories abaixo.

---

## Phase 3: User Story 1 - Navegação e workspace em português (Priority: P1) 🎯 MVP

**Goal**: sidebar, seletor de workspace, topbar e logo do shell em português,
sem inglês solto e sem quebrar o mapeamento label→ícone nem a navegação ativa.

**Independent Test**: abrir `/`, `/itsm`, `/agile`; nenhum item de menu,
título de seção ativa ou rótulo do seletor de workspace mostra inglês; ícone
correto ao lado de cada item.

### Implementation for User Story 1

- [x] T002 [P] [US1] Traduzir `NAV.itsm`/`NAV.agile` ("Home"→"Início",
      "Dashboard"→"Painel", "Assets"→"Ativos") e o fallback de
      `sectionLabel()` em `lib/nav.ts`
- [x] T003 [US1] Adicionar campo `icon` em `NavItem` e preencher por item em
      `lib/nav.ts`, removendo o lookup `NAV_ICONS[label]` (corrige o
      acoplamento label→ícone descrito em `research.md` D4) — depende de T002
- [x] T004 [US1] Atualizar `components/shell/app-sidebar.tsx`: consumir
      `item.icon` em vez de `NAV_ICONS[item.label]`, remover import
      `NAV_ICONS`/`Home` não usados, traduzir logo do shell
      ("ITSM+Agile"→"ITSM+Ágil") e comentário que citava "Dashboard" — depende
      de T003
- [x] T005 [P] [US1] Traduzir rótulo do workspace ágil ("Agile"→"Ágil") em
      `components/shell/workspace-switcher.tsx`
- [x] T006 [P] [US1] Traduzir `WORKSPACE_LABEL.agile` ("Agile"→"Ágil") em
      `components/shell/topbar.tsx`
- [x] T007 [P] [US1] Traduzir aba "Dashboard"→"Painel" e comentário
      correspondente em `components/agile/agile-tabs.tsx`
- [x] T008 [P] [US1] Traduzir título "Assets"→"Ativos" da seção
      `em-construcao/assets` em `app/(shell)/em-construcao/[secao]/page.tsx`

**Checkpoint**: navegação e workspace 100% em português; `tsc`/`eslint`
limpos; ícone correto em cada item confirmado visualmente.

---

## Phase 4: User Story 2 - Acessibilidade do Assistente em português (Priority: P2)

**Goal**: texto acessível (`sr-only`) dos botões de rolagem da conversa do
Assistente em português.

**Independent Test**: inspecionar nome acessível dos botões de rolagem do
`message-scroller` em `/ai/chat/[id]` — sem "Scroll to end"/"Scroll to start".

### Implementation for User Story 2

- [x] T009 [US2] Traduzir texto `sr-only` dos botões de rolagem
      ("Scroll to end"→"Ir para o fim da conversa", "Scroll to start"→"Ir
      para o início da conversa") em `components/ui/message-scroller.tsx`

**Checkpoint**: leitor de tela anuncia os controles de rolagem em português.

---

## Phase 5: User Story 3 - Varredura completa de KPIs, gráficos e estados (Priority: P3)

**Goal**: garantir que nenhum card de KPI, gráfico, estado ou rótulo residual
ficou em inglês fora dos pontos já cobertos pelas Stories 1 e 2.

**Independent Test**: grep por literais em inglês em `frontend/src/app` e
`frontend/src/components`, revisado contra falso positivo; zero ocorrências
de texto de UI em inglês.

### Implementation for User Story 3

- [x] T010 [US3] Rodar varredura de texto (grep) nos diretórios `app/` e
      `components/`, filtrando identificadores técnicos (`data-model.md`
      lista o resultado completo antes/depois)
- [x] T011 [P] [US3] Traduzir slice do donut "Volume por status"
      ("Retry"→"Retry agendado", consistente com o vocabulário já usado em
      `components/itsm/ticket-table.tsx`) em `app/(shell)/page.tsx`
- [x] T012 [P] [US3] Traduzir link de retorno da 404 ("Voltar para a
      Home"→"Voltar para o início") em `app/not-found.tsx`
- [x] T013 [US3] Re-rodar a varredura de T010 após T002-T012 e confirmar
      zero ocorrência residual (comando documentado em `quickstart.md` §2) —
      depende de T002, T004-T009, T011, T012

**Checkpoint**: varredura final sem nenhuma ocorrência de texto de UI em
inglês (SC-002).

---

## Phase 6: Achados de code review (fora do escopo original de i18n)

**Purpose**: dois problemas achados durante a auditoria de código que
acompanhou a tradução, corrigidos na mesma sessão por estarem em área
correlata (`board.tsx` usa `lib/nav`-adjacent patterns de estado local; não
bloqueiam nem são bloqueados pelas Stories 1-3, mas seguem documentados
como parte desta feature por terem sido descobertos durante ela). Ver
`research.md` D4/D5 para o raciocínio completo.

- [x] T014 [P] Corrigir race condition de transições concorrentes no board
      Kanban: adicionar flag `moving` que serializa `move()` e desabilita
      drag/select durante a requisição em flight, em
      `components/agile/board.tsx` (`Board` e `BoardCard`)
- [x] T015 Validar T003 (fix do acoplamento label→ícone) e T014 com
      `npx tsc --noEmit` + `npx eslint src` + `npm run build` — depende de
      T003, T014

**Checkpoint**: nenhuma transição concorrente corrompe o estado do board;
ícone de navegação não depende mais de string de label sincronizada à mão.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: validação final de todas as stories juntas

- [x] T016 Rodar `npx tsc --noEmit`, `npx eslint src` e `npm run build` em
      `frontend/` com todas as mudanças (T002-T015) aplicadas — depende de
      todas as tarefas anteriores
- [x] T017 Executar `quickstart.md` §3 e §4 (checagem visual das telas e do
      board) — depende de T016

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: vazia — não bloqueia nada
- **User Stories (Phase 3-5)**: podem come��ar após Setup; independentes
  entre si (arquivos não se sobrepõem, exceto T004 que só depende de T002/T003
  dentro da própria US1)
- **Achados de code review (Phase 6)**: independente das Stories 1-3;
  poderia ter sido feita em paralelo
- **Polish (Phase 7)**: depende de todas as fases anteriores

### User Story Dependencies

- **US1 (P1)**: sem dependência de outra story. Internamente: T002 → T003 → T004.
- **US2 (P2)**: sem dependência de US1 nem US3 — arquivo isolado (`message-scroller.tsx`).
- **US3 (P3)**: T010/T013 dependem de US1 e US2 estarem aplicadas (é a
  varredura de confirmação); T011/T012 são independentes entre si e de US1/US2.

### Parallel Opportunities

- T002, T005, T006, T007, T008 — arquivos diferentes, sem dependência entre si
- T011, T012 — arquivos diferentes
- T014 é independente de toda a Phase 3-5 (poderia ter rodado em paralelo)

---

## Parallel Example: User Story 1

```bash
# Depois de T002 (nav.ts) e T003 (campo icon):
Task: "Traduzir workspace-switcher.tsx (Agile→Ágil)"
Task: "Traduzir topbar.tsx (WORKSPACE_LABEL.agile→Ágil)"
Task: "Traduzir agile-tabs.tsx (Dashboard→Painel)"
Task: "Traduzir em-construcao/[secao]/page.tsx (Assets→Ativos)"
```

---

## Implementation Strategy

### MVP entregue

Phase 3 (US1) sozinha já resolve o ponto mais visível (sidebar, workspace,
logo — presentes em toda navegação). US2 e US3 são incrementos de cobertura
(acessibilidade e cauda longa) que não bloqueiam nem são bloqueados por US1.

### Ordem real de execução nesta sessão

Setup → US1 → US2 → US3 (varredura) → achados de code review (Phase 6,
descobertos durante a leitura de código feita para a Phase 3-5) → Polish.

---

## Notes

- Nenhuma tarefa de teste automatizado: projeto não tem suíte de frontend
  configurada (plan.md → Technical Context).
- Todas as tarefas desta lista já estão `[x]` — este arquivo é registro, não
  backlog. Qualquer nova ocorrência de texto em inglês encontrada depois
  desta feature é regressão, a ser tratada como bug novo, não reabertura
  destas tarefas.
