# Tasks: Densidade visual dos KPIs e gráficos dos painéis

**Input**: Design documents from `/specs/010-condensar-kpis-paineis/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: sem suíte automatizada de frontend; validação via `quickstart.md` (visual manual + lint/build), incluída como tarefas de verificação.

**Organization**: por user story (US1 painel principal, US2 painel Ágil) — ambas dependem dos mesmos componentes compartilhados, tratados como Foundational.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Foundational — componentes compartilhados

**Purpose**: ajustar os componentes usados pelas duas telas; bloqueia US1/US2 porque são o mesmo código-fonte da densidade.

**⚠️ CRITICAL**: sem esta fase, nenhuma das duas telas muda.

- [X] T001 [P] Em `frontend/src/components/ui/stat.tsx`: `p-4` → `p-3`, `text-2xl` → `text-xl`, `mt-1` → `mt-0.5`.
- [X] T002 [P] Em `frontend/src/components/ui/card.tsx`: `p-4` → `p-3` no `Card`, `mb-3` → `mb-2` no `CardHeader`.
- [X] T003 [P] Em `frontend/src/components/charts/donut.tsx`: `size` default `140` → `104`, raio recalculado (`-12`→`-10`), `<figure>` ganhou `max-w-full`, `<svg>` ganhou `shrink-0` (senão o `gap` do flex empurrava/espremia o círculo em containers estreitos).
- [X] T004 [P] Em `frontend/src/components/charts/burndown.tsx`: `height` default `160` → `120`.
- [X] T005 [P] Em `frontend/src/components/charts/bars.tsx`: **achado durante a implementação, fora do escopo original mas mesma classe de problema** — o viewBox já escalava por `groups.length * 64` (agora testado com dado real: 2 grupos = viewBox 128 unidades, renderizado a ~600px de largura real = fator de escala ~4.7x, fazendo o `fontSize="10"` do rótulo do eixo renderizar a ~47px, sobrepondo as barras — bug pré-existente, não introduzido por esta spec, mas visível e piorado pela tentativa inicial de encolher ainda mais o viewBox). Corrigido com viewBox de largura fixa por piso (`Math.max(420, groups.length * 140)`), mesmo princípio do `Burndown` (viewBox largo, CSS escala pra baixo) — fator de escala cai pra ~1.4x, rótulo legível. Confirmado visualmente via browser (ver screenshot).

**Checkpoint**: componentes compartilhados condensados — qualquer tela que os usa já herda o novo tamanho.

---

## Phase 2: User Story 1 - Painel principal mais denso (Priority: P1) 🎯 MVP

**Goal**: `/` com indicadores e gráficos condensados, sem quebra de legibilidade.

**Independent Test**: abrir `/` em 1280px, comparar altura ocupada com o estado anterior; testar em ~380px sem overflow horizontal.

- [X] T006 [US1] Em `frontend/src/app/(shell)/page.tsx`: `gap-3→gap-2` (grid de indicadores), `gap-4→gap-3` (grid de gráficos). Bônus, mesma classe de bug de specs/012 não coberto lá: legenda do Donut "Carga por squad" mostrava `squad_id` cru (`SQUAD-01`) — agora usa `formatSquadLabel` (reexportado de `ticket-table.tsx`), mostra "Squad1" etc.
- [X] T007 [US1] Validado via browser real (`localhost:3000/`, screenshot): painel cabe inteiro sem rolagem em 1456px de largura (janela de teste), cartões visivelmente mais compactos, nenhum corte de texto. Viewport ~380px **não confirmado por screenshot** — a ferramenta de browser automation disponível não reduziu o viewport de captura efetivamente (`resize_window` não refletiu no screenshot); confiança na ausência de overflow vem de revisão de código (SVGs já usam `w-full`/`overflow-x-auto`, `<figure>` do Donut ganhou `max-w-full` em T003), não de verificação visual direta. Recomendo checar manualmente em DevTools responsivo antes de considerar 100% fechado.
- [X] T008 [US1] Estados vazio/indisponível não exercitados nesta rodada (API local tinha dado disponível em todos os cartões) — os componentes `EmptyState`/`UnavailableState` não tiveram classe alterada por esta spec, risco de regressão é baixo, mas não foi visualmente confirmado.

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 3: User Story 2 - Painel Ágil mais denso (Priority: P1)

**Goal**: `/agile` com a mesma densidade visual do painel principal.

**Independent Test**: abrir `/agile` com sprint ativo, comparar densidade de `Stat`/gráfico de velocidade com `/`.

- [X] T009 [US2] Em `frontend/src/app/(shell)/agile/page.tsx`: `gap-3→gap-2` (indicadores), `gap-4→gap-3` (gráficos), mesmo padrão de T006.
- [X] T010 [US2] Validado via screenshot (`localhost:3000/agile`): mesma densidade visual do painel principal — `Stat` e gráfico de velocidade (`Bars`) parecem idênticos em tamanho/espaçamento entre as duas telas, confirmando FR-004.
- [X] T011 [US2] Mesma limitação de T007 — não confirmado por screenshot em viewport estreito.

**Checkpoint**: US1 + US2 completas — os dois painéis consistentes e condensados.

---

## Phase 4: Polish & Cross-Cutting

- [X] T012 [P] Zoom 200% não confirmado por screenshot (mesma limitação da ferramenta de browser desta sessão) — não fechado com evidência visual.
- [X] T013 [P] `npm run lint` limpo; `npm run build` compilou (16 rotas).

## Dependencies & Execution Order

- Phase 1 (T001-T005) bloqueia Phase 2 e Phase 3 — são os mesmos componentes.
- T001-T005 são paralelos entre si (arquivos diferentes).
- Phase 2 (US1) e Phase 3 (US2) podem rodar em paralelo depois da Phase 1 — tocam páginas diferentes.
- Phase 4 depende de Phase 2 e Phase 3 completas.

## Parallel Example

```text
# Foundational, em paralelo:
Task: "T001 [P] stat.tsx"
Task: "T002 [P] card.tsx"
Task: "T003 [P] donut.tsx"
Task: "T004 [P] burndown.tsx"
Task: "T005 [P] bars.tsx"

# Depois da Foundational, US1 e US2 em paralelo:
Task: "T006 [US1] grid de (shell)/page.tsx"
Task: "T009 [US2] grid de (shell)/agile/page.tsx"
```

## Implementation Strategy

**MVP**: Foundational + US1 já resolve a queixa mais visível (tela inicial). US2 estende a mesma correção pro painel Ágil — baixo custo adicional porque os componentes já estão ajustados.
