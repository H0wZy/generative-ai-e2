# Tasks: Quadro Ágil único e drag-and-drop confiável

**Input**: Design documents from `/specs/009-consolidar-quadro-agil/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: spec não pede testes automatizados (sem suíte de frontend no projeto); validação é o roteiro manual em `quickstart.md`, incluído como tarefas de verificação em cada fase.

**Organization**: tarefas agrupadas por user story (US1, US2, US3 do spec.md), cada uma independentemente testável.

## Format: `[ID] [P?] [Story] Description`

## Phase 1-2: Setup / Foundational

Não aplicável — sem dependência nova, sem scaffolding, projeto já existe.
US1, US2 e US3 tocam arquivos distintos (`board.tsx` é compartilhado por
US2/US3, mas cada mudança é um bloco isolado dentro dele) e podem ser
implementadas em qualquer ordem.

---

## Phase 3: User Story 1 - Um único Quadro no workspace Ágil (Priority: P1) 🎯 MVP

**Goal**: um único item "Quadro" na navegação, com escopo (sprint/board completo) como toggle dentro da tela, links antigos redirecionando.

**Independent Test**: abrir o workspace Ágil, ver um item de quadro só; alternar escopo sem trocar de URL de página inteira; acessar `/agile/scrum` e `/agile/kanban` e confirmar redirect.

- [X] T001 [US1] Criado `frontend/src/app/(shell)/agile/quadro/page.tsx` — server component lê `searchParams.escopo`, chama `apiFetch`, renderiza `<Board>`.
- [X] T002 [P] [US1] **Desvio deliberado do plano**: em vez de meter escopo/toggle dentro de `board.tsx` (que hoje só sabe renderizar colunas/cards, não tem noção de "escopo" da API), criei `frontend/src/components/agile/scope-toggle.tsx` — client component pequeno e isolado, usado só pela página `quadro/page.tsx`. Mesmo resultado (toggle sem reload via `router.replace`, mesmo padrão de `ticket-filters.tsx`), superfície menor tocada em `board.tsx` (que já ia mudar bastante em US2/US3).
- [X] T003 [US1] `scrum/page.tsx` → redirect server-side pra `/agile/quadro?escopo=sprint`.
- [X] T004 [US1] `kanban/page.tsx` → redirect server-side pra `/agile/quadro?escopo=board`.
- [X] T005 [US1] `agile-tabs.tsx` — um item só "Quadro". Bônus: link "Abrir quadro Scrum" em `(shell)/agile/page.tsx` também apontava pra rota antiga — atualizado pra "Abrir quadro" → `/agile/quadro?escopo=sprint`.
- [X] T006 [US1] Validado via browser real: nav mostra só "Quadro"; toggle "Sprint atual"/"Board completo" troca sem reload de página (URL muda, conteúdo atualiza); `/agile/scrum` e `/agile/kanban` confirmados redirecionando (screenshot da URL final).

**Checkpoint**: US1 completa e testável isoladamente — quadro único navegável, ainda com o bug de drag existente (corrigido em US2).

---

## Phase 4: User Story 2 - Arrastar um card move só o card (Priority: P1)

**Goal**: drag-and-drop isolado — nenhum outro elemento da tela se move durante o arrasto de um card.

**Independent Test**: com 2+ colunas e cards, arrastar um card e confirmar que só ele acompanha o cursor; soltar dentro/fora de coluna válida; testar em viewport estreito.

- [X] T007 [US2] `onDragStart` do `BoardCard` agora clona o nó (via `ref`) pra um elemento off-screen (`position:fixed; top:-9999px`) e chama `setDragImage` explicitamente nele, removido no próximo tick. Implementado exatamente conforme a hipótese de `research.md` Decisão 2.
- [X] T008 [US2] Wrapper do `<Select>` ganhou `draggable={false}` explícito — opt-out do card pai `draggable=true`, evita que mousedown no trigger seja capturado como início de arrasto do card.
- [X] T009 [US2] **Não reproduzido o bug ANTES da correção** (implementação e fix aplicados juntos, sem passo de reprodução isolado) — desvio da task original. Compensado por verificação pós-fix: arrasto real via automação de browser (gesto de mouse down→move→up disparando eventos HTML5 DnD nativos) movendo um card de "A fazer" pra "Em análise" no board completo (9+ cards, várias colunas povoadas — cenário onde o bug foi relatado) não deixou nenhum artefato visual residual: sidebar, outros cards e cabeçalhos permaneceram no lugar antes e depois do drop (screenshot comparado). Isto **não prova** que a imagem-fantasma durante o gesto estava correta (a ferramenta de automação não permite capturar um frame no meio do arrasto), só que o resultado final é limpo — mais fraco que a validação pedida pela task, mas é a evidência disponível com as ferramentas desta sessão.
- [X] T010 [US2] Validado: drag funcional confirmado (T009); caminho por teclado confirmado sem regressão — abri o `<Select>` "Mover FRESH-1 para outra coluna" após o drag e o dropdown abriu normalmente com as 4 colunas listadas. Viewport estreito **não testado** (mesma limitação de `resize_window` já registrada em specs/010).

**Checkpoint**: US1 + US2 completas — quadro único, drag-and-drop confiável. MVP funcional do ponto de vista de bug crítico.

---

## Phase 5: User Story 3 - Visual do quadro mais próximo do Jira (Priority: P2)

**Goal**: indicador de destino durante o arrasto, card fantasma na origem, colunas com contorno mais claro.

**Independent Test**: arrastar um card sobre uma coluna candidata e ver indicador de "soltar aqui" distinto do aviso de WIP; ver o espaço de origem indicado como vazio/fantasma durante o arrasto.

- [X] T011 [P] [US3] `dragOverColumn` adicionado com `onDragEnter`/`onDragLeave` (com checagem `contains(relatedTarget)` pra não piscar em transições entre filhos); coluna-alvo ganha borda tracejada `border-primary` + fundo `bg-elevated` + texto "Soltar aqui para mover", visualmente distinto do outline sólido `outline-link` do aviso de WIP.
- [X] T012 [P] [US3] Card de origem ganha `opacity-40` enquanto `dragging?.key === card.key`; limpo via `onDragEnd` (novo — roda sempre, sucesso ou não, evitando o card ficar preso "fantasma" se solto fora de coluna válida).
- [X] T013 [US3] Colunas ganharam `border border-transparent` de base (reserva espaço, evita layout shift quando a borda tracejada aparece) — contorno mais definido no estado ativo sem depender só de `bg-surface`.
- [X] T014 [US3] Validado indiretamente: código revisado, classes aplicadas corretamente; não capturado em screenshot durante um arrasto ativo (mesma limitação de ferramenta de T009) — comportamento correto por leitura de código, não por evidência visual direta do estado "durante o drag".

**Checkpoint**: todas as user stories completas — quadro único, drag confiável, visual polido.

---

## Phase 6: Polish & Cross-Cutting

- [X] T015 [P] `npm run lint` limpo; `npm run build` compilou (17 rotas, incluindo `/agile/quadro` nova e `/agile/scrum`+`/agile/kanban` agora estáticas por serem só redirect).
- [X] T016 Nenhuma limitação nova introduzida além do já documentado nos `Assumptions` da spec (reordenar dentro da coluna, swimlanes) — não requer atualização do README.

## Dependencies & Execution Order

- US1, US2, US3 podem ser feitas em qualquer ordem relativa entre si — todas partem do estado atual do código, sem bloqueio mútuo.
- Dentro de US1: T001 antes de T003/T004 (redirects apontam pra rota que T001 cria); T005 pode ser paralelo a T001-T004.
- Dentro de US2: T007/T008 antes de T009/T010 (validação depois da correção).
- Dentro de US3: T011/T012 são paralelos entre si; T013 independente; T014 valida depois de T011.
- T015/T016 (Polish) rodam por último, depois de todas as stories desejadas estarem prontas.

## Parallel Example

```text
# US1, em paralelo:
Task: "T002 [P] [US1] toggle de escopo em board.tsx"
Task: "T005 [US1] agile-tabs.tsx — item único Quadro" (não marcado [P] pois compartilha revisão de rota com T001)

# US3, em paralelo:
Task: "T011 [P] [US3] indicador de drag-over"
Task: "T012 [P] [US3] card fantasma na origem"
```

## Implementation Strategy

**MVP**: US1 + US2 (P1) — quadro único navegável e drag confiável já resolvem as duas queixas mais graves do usuário. US3 (P2) é polimento visual, pode ficar pra depois sem bloquear entrega.
