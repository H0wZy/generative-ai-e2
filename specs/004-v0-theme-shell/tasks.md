---
description: "Task list for feature implementation"
---

# Tasks: Unificação visual v0 — fundação de tokens + shell

**Input**: Design documents from `specs/004-v0-theme-shell/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ui-v0-theme.md, quickstart.md (todos lidos e prontos)

**Tests**: Não solicitados na spec — esta feature é puramente visual; validação é via `tsc`/`eslint` + verificação manual no navegador (quickstart.md), não teste automatizado novo.

**Organization**: Tarefas agrupadas por user story (US1 P1, US2 P2, US3 P3), com fase de Fundação bloqueante antes de todas.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência entre si)
- **[Story]**: US1, US2 ou US3 (mapeia pra `spec.md`)
- Caminhos são todos relativos a `frontend/`

## Achado durante o planejamento de tasks (correção sobre plan.md/contracts)

`plan.md`/`contracts/ui-v0-theme.md` afirmaram que `sidebar.tsx` e `workspace-switcher.tsx` não precisam de edição além da herança de token. **Isso está incompleto**: os dois arquivos referenciam diretamente um degrau de rampa (`bg-accent-800`, `text-neutral-100`, `text-neutral-300`) em vez de um token semântico — e as rampas `--color-neutral-*`/`--color-accent-*` **não mudam de valor** nesta rodada (`data-model.md`, linha "unchanged"). Sem correção, o link ativo da sidebar e a aba ativa do workspace switcher ficariam com a cor antiga (marrom/brass) mesmo depois do resto do app virar v0 — quebra direta de FR-001/SC-004. As tarefas T004/T005 abaixo corrigem isso trocando a referência de rampa por token semântico (`bg-primary`/`text-primary-foreground`, já cobertos por R2).

## Achado durante a implementação (mesma classe de bug, em `ui/button.tsx`)

`frontend/src/components/ui/button.tsx` variante `primary` usava `bg-primary text-neutral-100` — mesmo problema: `bg-primary` virou claro (v0) mas `text-neutral-100` (rampa, não token) já era quase branco no tema antigo, então o botão primário ficaria com texto quase branco sobre fundo quase branco (contraste quebrado, viola FR-005/SC-005). Corrigido para `text-primary-foreground` na mesma tarefa que tocou `globals.css` (T002/T003), fora do escopo original de `plan.md` (que previa zero edição em `ui/*`) pelo mesmo motivo do achado acima. Demais referências de rampa em `ui/*` (`button.tsx` secondary, `tag.tsx` todas as variantes) usam par-de-rampa internamente consistente (fundo e texto da mesma família, contraste preservado) — não quebram, só permanecem no visual antigo até a rodada dedicada de ITSM/Agile (fora de escopo aqui, conforme `spec.md` Assumptions).

---

## Phase 1: Setup

**Purpose**: Confirmar que a remoção do toggle de tema é segura antes de tocar em qualquer arquivo.

- [X] T001 Confirmar que `ThemeToggle` só é consumido em `frontend/src/components/shell/topbar.tsx` (`grep -rn "ThemeToggle" frontend/src`) e que nenhuma outra tela lê `document.documentElement.dataset.theme` ou `localStorage.getItem('theme')` além de `frontend/src/app/layout.tsx` (`grep -rn "dataset.theme\|localStorage.*theme" frontend/src`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Trocar a fundação de tokens — toda user story depende deste arquivo.

**⚠️ CRITICAL**: Nenhuma user story pode começar antes desta fase terminar.

- [X] T002 Em `frontend/src/app/globals.css`: substituir o valor de `--color-bg`, `--color-surface`, `--color-text`, `--color-muted`, `--color-link`, `--color-focus`, `--color-primary`, `--color-primary-hover`, `--color-elevated`, `--color-divider` em `:root` pelos valores da tabela em `data-model.md` (oklch literal, copiado de `.v0-assistant`); adicionar `--color-destructive: oklch(0.704 0.191 22.216)` e `--color-primary-foreground: oklch(0.205 0 0)` como tokens novos em `:root`; remover por completo o bloco `:root[data-theme="light"]` (linhas 80-95 hoje)
- [X] T003 Em `frontend/src/app/globals.css`, bloco `@theme inline` (hoje linhas 97-151): registrar `--color-destructive: var(--color-destructive)` e `--color-primary-foreground: var(--color-primary-foreground)` junto aos demais tokens semânticos, para existirem como utilitário Tailwind (`text-destructive`, `bg-destructive`, `text-primary-foreground`)

**Checkpoint**: Fundação pronta — herança de token já vale para todo `ui/*` e toda tela existente (FR-004, FR-009). User stories podem começar.

---

## Phase 3: User Story 1 - Navegação visualmente coesa entre Assistente e resto do produto (Priority: P1) 🎯 MVP

**Goal**: Sidebar, topbar e workspace switcher usam a mesma paleta escura do Assistente, incluindo estado ativo (que hoje referencia rampa antiga diretamente, não token).

**Independent Test**: Abrir `/assistant`, depois `/itsm` ou `/agile` — fundo, texto e superfícies da navegação batem com a paleta do Assistente, incluindo o item de menu ativo.

### Implementation for User Story 1

- [X] T004 [P] [US1] Em `frontend/src/components/shell/sidebar.tsx`: trocar `"bg-accent-800 text-neutral-100"` (link ativo, linha ~47) por `"bg-primary text-primary-foreground"`; trocar `"text-neutral-300"` (selo "em breve" no item ativo, linha ~58) por `"text-primary-foreground/70"`
- [X] T005 [P] [US1] Em `frontend/src/components/shell/workspace-switcher.tsx`: trocar `"bg-primary text-neutral-100"` (aba ativa, linha ~27) por `"bg-primary text-primary-foreground"`
- [X] T006 [US1] Verificação visual no navegador (depende de T002-T005): seguir `quickstart.md` passos 1-3 — abrir `/assistant`, `/` (ou `/itsm`), `/agile`; confirmar paleta idêntica na barra lateral e cabeçalho, incluindo o item ativo do menu e a aba ativa do workspace switcher

**Checkpoint**: User Story 1 completa e testável de forma independente — MVP entregável aqui.

---

## Phase 4: User Story 2 - Fim da alternância de tema claro/escuro (Priority: P2)

**Goal**: Nenhuma tela oferece mais alternância de tema; produto carrega sempre escuro, sem depender de preferência salva.

**Independent Test**: Percorrer o cabeçalho de qualquer tela do shell e confirmar ausência do controle; definir `localStorage.theme = 'light'` manualmente e confirmar que não tem efeito.

### Implementation for User Story 2

- [X] T007 [P] [US2] Deletar `frontend/src/components/shell/theme-toggle.tsx`
- [X] T008 [P] [US2] Em `frontend/src/components/shell/topbar.tsx`: remover `import { ThemeToggle } from "./theme-toggle"` e a tag `<ThemeToggle />` (linhas 7 e 23 hoje)
- [X] T009 [P] [US2] Em `frontend/src/app/layout.tsx`: remover a constante `themeInitScript` (linhas 18-22 hoje) e a tag `<script dangerouslySetInnerHTML={{ __html: themeInitScript }} />` (linha 32 hoje)
- [X] T010 [US2] Verificação no navegador (depende de T007-T009): seguir `quickstart.md` passo 6 — confirmar ausência do botão de alternância em qualquer tela do shell, e que `localStorage.setItem('theme', 'light')` seguido de reload não muda nada

**Checkpoint**: User Stories 1 e 2 funcionam juntas e de forma independente.

---

## Phase 5: User Story 3 - Componentes compartilhados herdam a nova paleta sem retrabalho tela a tela (Priority: P3)

**Goal**: Confirmar (sem editar) que `ui/*` e telas de ITSM/Agile/em-construcao já refletem a paleta nova por herança de token.

**Independent Test**: Abrir uma tela de ITSM ou Agile não tocada nesta rodada e ver cartões/tabelas/badges/estados já na paleta nova.

### Implementation for User Story 3

- [X] T011 [P] [US3] Confirmar (depende de T002-T003) que `frontend/src/components/ui/*.tsx` continua sem cor hardcoded nem referência direta a `neutral-*`/`accent-*`: `grep -nE "neutral-|accent-[0-9]|#[0-9a-fA-F]{3,6}|oklch\(" frontend/src/components/ui/*.tsx` deve retornar vazio — **achado**: não retornou vazio (`button.tsx` secondary, `tag.tsx` todas variantes), mas nenhuma quebra de contraste real (ver "Achado durante a implementação" acima); único caso quebrado (`button.tsx` primary) já corrigido
- [X] T012 [US3] Verificação no navegador (depende de T002-T003, T011): seguir `quickstart.md` passo 4 — abrir uma tela de ITSM ou Agile com cartões/tabela/badge/estado vazio e confirmar paleta nova com texto legível, sem ter editado o arquivo da tela
- [X] T013 [P] [US3] Verificação no navegador (depende de T002-T003): seguir `quickstart.md` passo 5 — abrir `frontend/src/app/(shell)/em-construcao/[secao]/page.tsx` e confirmar paleta nova

**Checkpoint**: As três user stories funcionam de forma independente.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Checks estáticos e de contraste que cobrem todas as stories.

- [X] T014 [P] `cd frontend && npx tsc --noEmit` — zero erro novo
- [X] T015 [P] `cd frontend && npx eslint src/components/shell src/app/globals.css src/app/layout.tsx` — zero erro novo
- [X] T016 Verificação de contraste medido no DevTools (depende de T002-T005) por `quickstart.md` seção "Verificação de contraste": confirmar que os pares de `research.md` R2 batem na prática, e que nenhum texto claro sólido aparece sobre `--color-destructive` cheio (regra R2)
- [X] T017 Rodar `quickstart.md` "Critério de conclusão" por inteiro, de ponta a ponta, como último check antes de reportar a feature concluída

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependência — roda primeiro
- **Foundational (Phase 2)**: depende de T001 — BLOQUEIA as três user stories
- **User Stories (Phase 3-5)**: todas dependem da Foundational; entre si são independentes (podem rodar em qualquer ordem ou em paralelo)
- **Polish (Phase 6)**: depende de todas as user stories completas

### Parallel Opportunities

- T004 e T005 (arquivos diferentes) em paralelo
- T007, T008, T009 (arquivos diferentes) em paralelo
- T011 e T013 em paralelo
- T014 e T015 em paralelo
- US1, US2 e US3 podem ser feitas em qualquer ordem entre si após a Foundational (nenhuma depende do código das outras, só do token comum)

---

## Parallel Example: User Story 1

```bash
# T004 e T005 em paralelo (arquivos diferentes, ambos só dependem de T002/T003):
Task: "sidebar.tsx — trocar bg-accent-800/text-neutral-100/text-neutral-300 por bg-primary/text-primary-foreground"
Task: "workspace-switcher.tsx — trocar text-neutral-100 por text-primary-foreground na aba ativa"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (Setup) → Phase 2 (Foundational, bloqueante)
2. Phase 3 (US1) → parar e validar com `quickstart.md` passos 1-3
3. Nesse ponto: sidebar/topbar/workspace-switcher já batem 100% com o Assistente — entregável demonstrável mesmo sem remover o toggle de tema ainda

### Incremental Delivery

1. Setup + Foundational → fundação pronta
2. US1 → validar → MVP visual pronto
3. US2 → validar → produto dark-only, sem controle órfão
4. US3 → validar (sem código novo, só confirmação) → herança de token provada em ITSM/Agile/em-construcao
5. Polish → checks estáticos + contraste medido → fechar a rodada

---

## Notes

- [P] = arquivos diferentes, sem dependência entre si
- Nenhuma tarefa toca `frontend/src/components/ui/*` — a prova da spec é herança sem edição (T011)
- Commitar depois de cada fase (Setup, Foundational, cada US, Polish), não tarefa a tarefa — mudança é pequena o bastante para isso sem perder rastreabilidade
- Se `quickstart.md` T016/T017 revelar um par de contraste que reprova, voltar para `data-model.md`/`research.md` antes de ajustar o valor do token (manter "medido, não estimado")
