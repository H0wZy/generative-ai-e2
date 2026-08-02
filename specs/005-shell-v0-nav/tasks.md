---

description: "Task list for specs/005-shell-v0-nav"
---

# Tasks: Navegação do shell com ícones, colapso e largura estável

**Input**: Design documents from `/specs/005-shell-v0-nav/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-v0-nav.md, quickstart.md

**Tests**: Não solicitados no spec (US1-US3 não pedem testes automatizados) — validação é checagem estática (`tsc`/`eslint`) + verificação manual em navegador, igual às rodadas 002-004.

**Organization**: Tasks agrupadas por user story (spec.md). Nenhuma dependência nova, nenhum diretório novo — todo arquivo já existe.

## Path Conventions

Web app já existente: `frontend/src/` (Next.js). Nenhum caminho novo introduzido nesta rodada (ver plan.md → Project Structure).

---

## Phase 1: Setup

**Purpose**: Confirmar pré-requisitos antes de tocar código.

- [X] T001 Confirmar que `lucide-react` está em `frontend/package.json` (dependência já usada por `components/assistant/conversation-sidebar.tsx`) e que `npm run dev` sobe sem erro a partir de `frontend/`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Consolidar o mapa de ícones num único lugar antes de qualquer user story consumi-lo — evita que US1 e a limpeza do Assistente peguem duas cópias divergentes do mesmo `Record`.

**⚠️ CRITICAL**: T002 bloqueia T004-T007 (sidebar nova) e T008 (import no Assistente).

- [X] T002 Mover `ICONS: Record<string, LucideIcon>` de `frontend/src/components/assistant/conversation-sidebar.tsx` (linhas 38-49) para `frontend/src/lib/nav.ts`, exportado como `NAV_ICONS`, com a tabela rótulo→ícone de `data-model.md` (import de `lucide-react`: `Home, LayoutDashboard, Boxes, BookOpen, Workflow, Sparkles, Settings, ListTodo, KanbanSquare, Blocks`)
- [X] T003 Atualizar `frontend/src/components/assistant/conversation-sidebar.tsx` para importar `NAV_ICONS` de `@/lib/nav` em vez do `ICONS` local removido em T002 (mesmo uso: `NAV_ICONS[item.label] ?? Home`, linha 202) — comportamento e visual do Assistente não mudam

**Checkpoint**: `NAV_ICONS` existe em `lib/nav.ts`, Assistente continua idêntico visualmente usando o import novo. A partir daqui US1 pode começar.

---

## Phase 3: User Story 1 - Barra lateral do shell ganha ícones e botão de colapsar iguais ao Assistente (Priority: P1) 🎯 MVP

**Goal**: Sidebar do shell (ITSM/Agile) mostra ícone por item de menu e oferece colapsar/expandir (280px/68px) em telas largas, igual ao padrão do Assistente — reaproveitando os tokens semânticos já unificados (research.md R2), sem novo namespace de cor.

**Independent Test**: Abrir `/itsm` e `/agile`, confirmar ícone em cada item; clicar em colapsar/expandir e confirmar troca de largura e comportamento do alternador de workspace/selo "em breve" (quickstart.md passos 1-2).

### Implementation for User Story 1

- [X] T004 [US1] Reescrever `frontend/src/components/shell/sidebar.tsx`: adicionar `NAV_ICONS[item.label] ?? Home` ao lado do rótulo de cada item (import de `@/lib/nav`), mantendo `pathname`/`useActiveWorkspace`/lógica de item ativo e selo "em breve" existentes
- [X] T005 [US1] Em `frontend/src/components/shell/sidebar.tsx`, adicionar estado local `collapsed` (`useState(false)`) e botão de colapsar/expandir (ícones `PanelLeftClose`/`PanelLeftOpen` de `lucide-react`), visível só em `md:`, trocando a largura de `md:w-56` fixo para `md:w-[280px]` (expandida) / `md:w-[68px]` (colapsada) — mobile (`overflow-x-auto`, faixa horizontal) fica inalterado
- [X] T006 [US1] Em `frontend/src/components/shell/sidebar.tsx`, esconder rótulo de texto e selo "em breve" quando `collapsed` (mantendo ícone e `aria-current`/destaque do item ativo visíveis), seguindo o mesmo padrão de `conversation-sidebar.tsx` (`cn(collapsed && "lg:hidden")`, ajustado para `md:`)
- [X] T007 [US1] Atualizar `frontend/src/components/shell/workspace-switcher.tsx` (ou o componente pai em `sidebar.tsx`) para não renderizar o alternador ITSM/Agile quando a sidebar está colapsada, replicando a regra que `conversation-sidebar.tsx` já aplica ao próprio bloco de troca de workspace

**Checkpoint**: US1 completa e testável — ícones em todo item, colapso funcional, alternador de workspace se comporta corretamente nos dois estados.

---

## Phase 4: User Story 2 - Largura da barra lateral deixa de variar entre páginas (Priority: P2)

**Goal**: Confirmar (e reforçar estruturalmente, via US1) que a largura da sidebar nunca depende do conteúdo de `<main>`.

**Independent Test**: Medir `nav[aria-label="Navegação principal"]` em `/itsm`, `/agile/backlog`, `/itsm/new` — mesmo valor nos três, expandida e colapsada (quickstart.md passo 3); testar redimensionamento cruzando `768px` em duas páginas diferentes (quickstart.md passo 4).

### Implementation for User Story 2

- [X] T008 [US2] Validar em navegador (Chrome), com `frontend` rodando: medir `getBoundingClientRect().width` da sidebar em `/itsm`, `/agile/backlog`, `/itsm/new`, nos dois estados (expandida/colapsada) — deve dar 280px/68px nos três, sem variação (research.md R1 já confirmou isso no código anterior; esta task reconfirma pós-reescrita de T004-T007)
- [X] T009 [US2] Validar em navegador: redimensionar a janela cruzando 768px em pelo menos duas páginas do shell diferentes e confirmar que a transição barra-fixa ↔ faixa-horizontal acontece no mesmo ponto nas duas (FR-004)

**Checkpoint**: Largura comprovadamente estável e responsivo consistente — bug relatado pelo usuário fechado com evidência, não só suposição.

---

## Phase 5: User Story 3 - Cabeçalho do shell casa visualmente com o cabeçalho do Assistente (Priority: P3)

**Goal**: Altura, espaçamento e borda do `<header>` do shell equivalentes ao `<header>` do Assistente.

**Independent Test**: Comparar visualmente `/assistant` com qualquer página do shell (quickstart.md passo 5).

### Implementation for User Story 3

- [X] T010 [US3] Ajustar `frontend/src/components/shell/topbar.tsx`: trocar `min-h-14 items-center justify-between gap-4 border-b border-divider px-4` por `items-center justify-between gap-4 border-b border-divider px-4 py-3 md:px-6` (equivalente ao `<header>` de `components/assistant/ai-assistant.tsx`), mantendo o conteúdo (`<h1>` com seção ativa + workspace) sem mudança

**Checkpoint**: Cabeçalho do shell visualmente equivalente ao do Assistente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Checagens finais que cobrem as três user stories juntas.

- [X] T011 [P] Rodar `cd frontend && npx tsc --noEmit` e `npx eslint .` — zero erro novo
- [X] T012 Rodar o checklist completo de `quickstart.md` (passos 1-6) em navegador, incluindo confirmação de contraste visual nos dois estados de colapso e nos dois workspaces (FR-008)
- [X] T013 Confirmar que nenhuma página de `frontend/src/app/(shell)/**` precisou de edição (fora de escopo desta rodada, spec Assumptions) — `git status`/`git diff --stat` só deve listar os arquivos de `contracts/ui-v0-nav.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependência — roda primeiro.
- **Foundational (Phase 2)**: depende de Setup. T002 bloqueia T003 e toda a Phase 3 (T004-T007 usam `NAV_ICONS`).
- **US1 (Phase 3)**: depende de Foundational. T004 → T005 → T006 → T007 (mesmo arquivo, `sidebar.tsx`, sequencial — T007 pode tocar `workspace-switcher.tsx` em paralelo com T006 se preferir, mas ambos dependem de T005 existir).
- **US2 (Phase 4)**: depende de US1 completa (a garantia de largura é entregue pela reescrita de T005; US2 só valida). Não é paralelizável com US1.
- **US3 (Phase 5)**: independente de US1/US2 (arquivo diferente, `topbar.tsx`) — pode rodar em paralelo com Phase 3/4 se houver mais de uma pessoa, mas não depende delas.
- **Polish (Phase 6)**: depende de US1, US2 e US3 completas.

### Parallel Opportunities

- T001 (Setup) não é paralelizável com nada (é só verificação, roda uma vez).
- T003 pode rodar em paralelo com o início de T004 (arquivos diferentes: `conversation-sidebar.tsx` vs `sidebar.tsx`), desde que T002 já tenha terminado.
- Phase 5 (US3, `topbar.tsx`) é paralelizável com Phase 3/4 inteiras (arquivo diferente, zero dependência).
- T011 [P] (checagem estática) pode rodar em paralelo com T012 (validação manual).

---

## Parallel Example: Foundational + US3

```bash
# Depois de T002 (NAV_ICONS criado):
Task: "Atualizar conversation-sidebar.tsx para importar NAV_ICONS (T003)"
Task: "Ajustar topbar.tsx para casar com header do Assistente (T010, US3)"
# Os dois podem rodar juntos — arquivos diferentes, nenhuma dependência entre si.
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 (Setup) → Phase 2 (Foundational: `NAV_ICONS`) → Phase 3 (US1: ícones + colapso).
2. **PARAR e VALIDAR**: rodar quickstart.md passos 1-2 antes de seguir.
3. US1 sozinha já entrega o valor mais visível do pedido do usuário (ícones + colapso).

### Incremental Delivery

1. Setup + Foundational → base pronta.
2. US1 → validar independentemente → sidebar com ícones/colapso no ar.
3. US2 → validar independentemente → largura estável confirmada com evidência.
4. US3 → validar independentemente → cabeçalho casado com o Assistente.
5. Polish → checagem estática + checklist completo + confirmação de escopo.
