---

description: "Task list — Consolidação de UI em shadcn e correção de scroll/reveal"
---

# Tasks: Consolidação de UI em shadcn e correção de scroll/reveal

**Input**: Design documents from `/specs/006-shadcn-ui-consolidation/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/ui-shadcn.md](./contracts/ui-shadcn.md), [quickstart.md](./quickstart.md)

**Tests**: Nenhuma tarefa de teste automatizado. O projeto não tem suíte de teste
de frontend e a spec não pediu TDD. A verificação desta rodada é **medição
instrumentada no navegador** (`quickstart.md` V1–V6), que é o que os critérios
de sucesso exigem — altura rolável, monotonicidade de `scrollHeight`, valor
computado de token. Cada história tem suas tarefas de verificação explícitas.

**Organization**: Tarefas agrupadas por história de usuário, cada uma
implementável e verificável de forma independente.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos distintos, sem dependência pendente)
- **[Story]**: a qual história a tarefa pertence (US1, US2, US3, US4)
- Caminho de arquivo exato em toda tarefa

## Path Conventions

Web app — todo o trabalho fica em `frontend/`. Nada em `backend/`, `rag/` ou
`docs/`. Caminhos abaixo são relativos à raiz do repositório.

## Nota de sequenciamento

O `plan.md` descreve a reconciliação de tokens como "Fase 1". Aqui ela aparece
dentro da **US3**, e não como fase Foundational global, por um motivo
verificado: US1 (`sr-only`) e US2 (typewriter) **não dependem de cor nenhuma** —
são bloco contentor e reserva de altura. Colocar a mudança de maior risco na
frente atrasaria a entrega do P1 sem necessidade. A dependência real que o plano
aponta é *tokens antes da migração de componentes*, e essa ordem é preservada
dentro da US3. A ordem de execução final passa a ser a das prioridades da spec:
US1 → US2 → US3 → US4.

---

## Phase 1: Setup

**Purpose**: garantir ambiente rodando antes de medir qualquer coisa

- [X] T001 Subir o frontend em modo desenvolvimento a partir de `frontend/` (`npm install && npm run dev`) e confirmar que `http://localhost:3000` responde, com backend no ar para as telas de ITSM/Agile terem dado real
- [X] T002 Confirmar que o diff de `frontend/package.json` e `frontend/package-lock.json` está vazio no início da rodada, para que SC-008 (nenhuma dependência nova) seja verificável por comparação no fim

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: capturar o estado "antes". Sem essa linha de base não há como provar
SC-001, SC-003, SC-004 nem a comparação visual de SC-007 — ela bloqueia a
**verificação** de todas as histórias, ainda que não bloqueie a implementação.

**⚠️ CRITICAL**: capturar antes de alterar qualquer arquivo. Depois de mudado, a
linha de base é irrecuperável.

- [X] T003 [P] Registrar a medição de contenção em `/agile/kanban` e `/agile/scrum` com a janela baixa o suficiente para a coluna mais cheia transbordar, anotando `scrollHeight`, `clientHeight` e o delta (referência conhecida: 1905 / 853 / 1052) — procedimento em `quickstart.md` V1
- [X] T004 [P] Registrar a amostragem quadro a quadro da revelação em `/assistant` numa conversa com histórico, anotando o menor `scrollTop` e a maior queda de `scrollHeight` (referência conhecida: `scrollTop` 3460 → 0, `scrollHeight` 4129 → 3821) — procedimento em `quickstart.md` V2
- [X] T005 [P] Registrar os valores computados dos utilitários de cor da tabela de `data-model.md` §1 e capturar imagem de cada tela (`/`, `/itsm`, `/agile`, `/agile/backlog`, `/agile/scrum`, `/agile/kanban`, `/assistant`) como base da comparação visual de SC-007

**Checkpoint**: linha de base registrada — implementação pode começar

---

## Phase 3: User Story 1 - Quadro nunca escapa dos limites da tela (Priority: P1) 🎯 MVP

**Goal**: eliminar a rolagem de documento que tira a navegação da tela no Kanban
e no Scrum, deixando um scroll por eixo na região correta.

**Independent Test**: abrir `/agile/kanban` numa janela menor que o conteúdo da
coluna mais cheia e confirmar `scrollHeight - clientHeight === 0`, com a barra
lateral inteiramente visível e a rolagem da coluna funcionando.

### Implementação

- [X] T006 [US1] Remover o `<span className="sr-only">Mover {card.key} para</span>` de `frontend/src/components/agile/board.tsx` (linha ~191), mantendo intacto o `aria-label` do `<select>` irmão, que já é o nome acessível efetivo do controle
- [X] T007 [US1] Tornar o `<main>` de `frontend/src/components/shell/shell-chrome.tsx` um bloco contentor (`relative`), para que descendentes posicionados absolutamente sejam ancorados na área de conteúdo e não no documento

### Verificação

- [X] T008 [P] [US1] Confirmar em `/agile/kanban` que `document.documentElement.scrollHeight - clientHeight === 0` e que a consulta de absolutos escapando de `quickstart.md` V1 retorna lista vazia
- [X] T009 [P] [US1] Repetir a verificação de T008 em `/agile/scrum` (mesmo componente `Board`, precisa se comportar igual)
- [X] T010 [P] [US1] Confirmar à mão que rolar sobre uma coluna move só aquela coluna e que barra lateral, cabeçalho e abas permanecem fixos (C1.3, C1.5)
- [X] T011 [US1] Confirmar que arrastar e soltar um cartão entre colunas continua funcionando com mouse, e que mover pelo seletor continua funcionando só com teclado (C5.3, C3.7)

**Checkpoint**: US1 entregue e verificável isoladamente — este é o MVP

---

## Phase 4: User Story 2 - Resposta aparece progressivamente sem solavanco (Priority: P2)

**Goal**: revelar a resposta com sensação de digitação, já formatada, sem que a
conversa salte para o topo nem o conteúdo encolha.

**Independent Test**: numa conversa com histórico, enviar pergunta e amostrar
`scrollTop`/`scrollHeight` quadro a quadro; `encolheu` e `voltouAoTopo` devem
ser ambos `false`.

### Implementação

- [X] T012 [US2] Reescrever `frontend/src/components/assistant/typewriter-message.tsx` para reservar a altura final desde o primeiro quadro: empilhar na mesma célula de grid uma cópia completa do markdown — invisível e fora da árvore de acessibilidade (`aria-hidden`) — e a cópia revelada, de modo que a célula assuma sempre a altura da completa
- [X] T013 [US2] Adicionar supressão por `prefers-reduced-motion: reduce` em `frontend/src/components/assistant/use-typewriter.ts`, devolvendo o texto completo de imediato (sem revelação e sem cópia dupla) quando a preferência estiver ativa (FR-012)
- [X] T014 [US2] Remover o efeito `scrollToEnd` e o import de `useMessageScroller` de `frontend/src/components/assistant/conversation-view.tsx`, restaurando a chamada `useTypewriter` como única responsável pelo ritmo — sem o colapso de altura, o mecanismo de âncora do rolador já entrega o comportamento correto
- [X] T015 [US2] Ajustar a regra `.v0-typewriter > :last-child::after` em `frontend/src/app/globals.css` para que o cursor continue aparecendo após o último bloco **da cópia revelada**, sem vazar para a cópia invisível de reserva

### Verificação

- [X] T016 [P] [US2] Confirmar pela amostragem de `quickstart.md` V2 que `encolheu === false` (SC-004 / FR-008) e `voltouAoTopo === false` (SC-003 / FR-009)
- [X] T017 [P] [US2] Confirmar que nenhum quadro da revelação exibe `###`, `**` ou `|` literais — markdown formatado do início ao fim (C2.2 / FR-007)
- [X] T018 [P] [US2] Confirmar que rolar manualmente durante a revelação não é desfeito pelo sistema (C2.5 / FR-010) e que abrir uma conversa do histórico mostra o conteúdo completo sem animação (C2.6 / FR-011)
- [X] T019 [US2] Confirmar com *Emulate CSS media feature prefers-reduced-motion: reduce* que a resposta aparece inteira de uma vez (C2.7 / FR-012)

**Checkpoint**: US1 e US2 entregues — os dois defeitos relatados estão fechados

---

## Phase 5: User Story 3 - Controles com aparência e comportamento uniformes (Priority: P3)

**Goal**: um só vocabulário de componente e de token, com todo controle no tema
do produto e operável por teclado.

**Independent Test**: percorrer todas as telas comparando cada tipo de controle;
nenhum widget nativo do sistema, nenhum utilitário de cor resolvendo para
transparente, foco visível em tudo.

### Sub-fase 5A — Reconciliação de tokens (bloqueia 5B)

**⚠️ CRITICAL**: nenhuma migração de componente pode começar antes de 5A passar
na verificação T026. Sem isso, todo componente migrado nasce branco ou
transparente (`research.md` §R3).

- [X] T020 [US3] Em `frontend/src/app/globals.css`, levar os valores escuros do bloco `.dark` para `:root` e **remover o bloco `.dark`** (linhas ~421–453), que é CSS morto — o `<html>` nunca recebe a classe
- [X] T021 [US3] Em `frontend/src/app/globals.css`, remover as entradas auto-referentes do `@theme inline` (padrão `--color-X: var(--color-X)`) que formam ciclo e invalidam `bg-muted`, `bg-card` e `bg-accent`
- [X] T022 [US3] Em `frontend/src/app/globals.css`, apontar os nomes shadcn para a paleta do projeto conforme a tabela de mapeamento de `data-model.md` §2.1, preservando intactas a rampa `accent-100…900` (identidade brass) e as rampas `neutral-*` e `accent-2-*`
- [X] T023 [US3] Renomear `text-muted` → `text-muted-foreground` nas 79 ocorrências sob `frontend/src/`, liberando o nome `muted` para significar superfície; a troca é mecânica e **sem delta visual** (`oklch(0.708)` antes e depois). Conferir com `grep -rn "\btext-muted\b" frontend/src/ | wc -l` retornando 0
- [X] T024 [US3] Ajustar o `@layer base` de `frontend/src/app/globals.css` para não aplicar `border-border`/`bg-background` claros como padrão global a todo elemento, e remover a duplicidade entre a regra `body` fora de layer e a de dentro
- [X] T025 [US3] Confirmar que `frontend/src/components/ui/button.tsx`, `context-menu.tsx` e `message-scroller.tsx` passam a resolver corretamente **sem edição** (o `hover:bg-muted` deles deixa de ser transparente); só editar se alguma classe permanecer inválida
- [X] T026 [US3] Verificar 5A pelo procedimento de `quickstart.md` V3: nenhum utilitário em `rgba(0,0,0,0)`, `bg-background` escuro, `border-border` discreto, `bg-accent-500` = `rgb(201,162,39)` e `bg-accent-800` = `rgb(92,74,18)` inalterados, `.dark` ausente do arquivo. Comparar todas as telas com as imagens de T005 (SC-007) antes de seguir

### Sub-fase 5B — Primitivas em `components/ui/`

- [X] T027 [P] [US3] Criar `frontend/src/components/ui/select.tsx` sobre `@base-ui/react/select`, no estilo base-nova já usado em `button.tsx`, com lista temática, navegação por teclado e opção em foco visível (C3.1, C3.2)
- [X] T028 [P] [US3] Criar `frontend/src/components/ui/input.tsx` e `frontend/src/components/ui/textarea.tsx` sobre `@base-ui/react/input`, alinhados aos tokens do projeto
- [X] T029 [P] [US3] Migrar `frontend/src/components/ui/card.tsx` para o Card do shadcn, preservando a API `title`/`action` hoje consumida pelo painel — ou ajustando as chamadas na mesma tarefa, se a API mudar
- [X] T030 [P] [US3] Migrar `frontend/src/components/ui/table.tsx` para o Table do shadcn
- [X] T031 [P] [US3] Migrar `frontend/src/components/ui/skeleton.tsx` para o Skeleton do shadcn
- [X] T032 [P] [US3] Migrar `frontend/src/components/ui/tag.tsx` para Badge, preservando exatamente os 5 tons e os pares de contraste já verificados (`bg-accent-800/text-accent-200` etc.) — I-03 proíbe mudar esses valores
- [X] T033 [US3] Confirmar que nenhuma dependência nova entrou: `git diff frontend/package.json frontend/package-lock.json` vazio (SC-008, I-04)

### Sub-fase 5C — Consumidores, por área

- [X] T034 [P] [US3] Substituir os `<select>` e `<input>` nativos de `frontend/src/components/itsm/ticket-filters.tsx` pelos componentes de T027/T028
- [X] T035 [P] [US3] Substituir os `<select>` e `<input>`/`<textarea>` nativos de `frontend/src/components/itsm/ticket-form.tsx` pelos componentes de T027/T028
- [X] T036 [P] [US3] Substituir os `<input>` de `frontend/src/components/itsm/reprocess-button.tsx` e `frontend/src/components/itsm/resolve-button.tsx` pelos componentes de T028, e os disparadores por `Button`
- [X] T037 [US3] Substituir o `<select>` de coluna do cartão em `frontend/src/components/agile/board.tsx` pelo Select de T027, **preservando a operação só por teclado** — este seletor é a alternativa acessível ao arrastar e soltar (FR-018, C3.7) e não pode regredir
- [X] T038 [P] [US3] Substituir os 5 `<button>` brutos de `frontend/src/components/shell/app-sidebar.tsx` por `Button`, mantendo as classes de token atuais para não alterar a aparência
- [X] T039 [P] [US3] Substituir o `<button>` bruto de `frontend/src/components/shell/topbar.tsx` por `Button`, mantendo a aparência
- [X] T040 [P] [US3] Substituir os `<button>`/`<textarea>` brutos de `frontend/src/components/assistant/chat-composer.tsx` por `Button`/`Textarea`, **preservando as classes `v0-*`** — o tema do Assistente é escopado e não muda nesta rodada (I-05)
- [X] T041 [P] [US3] Substituir os `<button>` brutos de `frontend/src/components/assistant/source-accordion.tsx`, `empty-state.tsx`, `conversation-view.tsx` e `ai-assistant.tsx` por `Button`, também preservando as classes `v0-*` (I-05)
- [X] T042 [US3] Manter a rolagem nativa das colunas do quadro em `frontend/src/components/agile/board.tsx` — **não** trocar por ScrollArea. A aparência já vem da regra global de `scrollbar`; trocar arriscaria regredir o arrastar e soltar sem ganho (`research.md` §R4). Aplicar ScrollArea apenas onde o conteúdo for passivo

### Verificação

- [X] T043 [P] [US3] Percorrer `/`, `/itsm`, `/agile`, `/agile/backlog`, `/agile/scrum`, `/agile/kanban` e `/assistant` confirmando que todo campo de seleção abre no tema do produto e nenhum widget nativo permanece (SC-005, C3.1)
- [X] T044 [P] [US3] Percorrer cada tela só com `Tab`, confirmando foco visível em todo controle e ordem de tabulação igual à ordem visual (SC-006, C3.4, C3.5)
- [X] T045 [US3] Comparar cada tela com as imagens de T005 confirmando paleta, espaçamento e densidade inalterados (SC-007, C3.9), e confirmar que a tela do Assistente segue idêntica (C5.4, I-05)

**Checkpoint**: vocabulário único de token e de componente em todo o produto

---

## Phase 6: User Story 4 - Entrada para "Novo chamado" deixa de ser um bloco branco (Priority: P3)

**Goal**: apresentar a criação de chamado como cartão coerente com o painel, sem
o retângulo branco de alto contraste.

**Independent Test**: abrir `/itsm`, confirmar que a entrada não é mais o
elemento de maior contraste da tela e que continua sendo link real, alcançável
por teclado.

- [X] T046 [US4] Substituir o `<Link>` estilizado como botão em `frontend/src/app/(shell)/itsm/page.tsx` (linhas ~59–64) por uma superfície de cartão clicável, **mantendo `<Link>` real com `href="/itsm/new"`** — não converter em `<button>` com navegação por `onClick`, o que quebraria semântica, abertura em nova aba e anúncio como link (C4.2)
- [X] T047 [P] [US4] Confirmar que a entrada é `<a>` com `href="/itsm/new"`, alcançável por `Tab`, com foco visível, e que `Enter` navega (C4.2, C4.3, C4.4)
- [X] T048 [P] [US4] Confirmar visualmente que a entrada deixou de ser o elemento de maior contraste da tela e que a tela mantém uma única ação primária (C4.1, C4.5)

**Checkpoint**: todas as histórias entregues

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T049 [P] Rodar `npx tsc --noEmit` a partir de `frontend/` e confirmar saída vazia (C5.1)
- [X] T050 [P] Rodar `npx eslint .` a partir de `frontend/` e confirmar que só resta o apontamento **pré-existente** `react-hooks/set-state-in-effect` em `frontend/src/lib/nav.ts` (`useActiveWorkspace`), declarado fora de escopo — nenhum erro novo (C5.2)
- [X] T051 [P] Confirmar novamente que `git diff frontend/package.json frontend/package-lock.json` está vazio (SC-008)
- [X] T052 Reexecutar V1 e V2 de `quickstart.md` no fim da rodada, garantindo que a migração da US3 não reintroduziu o vazamento de rolagem nem o solavanco da revelação
- [X] T053 [P] Confirmar que nenhum literal de cor entrou em componente e que nenhum utilitário de cor resolve para `transparent` sem intenção (I-01, I-02, C3.8)
- [ ] T054 Atualizar a seção "o que ficou de fora" do README com os itens deliberadamente adiados: streaming real token a token, aviso de hidratação em `/assistant` quando o workspace persistido difere do renderizado no servidor, e o apontamento de lint pré-existente em `useActiveWorkspace` (Constituição §V exige limitação documentada como decisão)

---

## Dependencies

### Entre histórias

```
Setup (T001–T002)
   └─> Foundational / linha de base (T003–T005)   ⚠️ antes de qualquer alteração
          ├─> US1 (T006–T011)   independente
          ├─> US2 (T012–T019)   independente
          ├─> US3 (T020–T045)   independente de US1/US2
          │      └─ 5A tokens (T020–T026) ──bloqueia──> 5B (T027–T033) ──> 5C (T034–T042)
          └─> US4 (T046–T048)   depende de US3-5A (precisa do token de cartão correto)
                 └─> Polish (T049–T054)
```

- **US1 e US2 são mutuamente independentes** e independentes da US3 — tocam
  bloco contentor e altura, não cor. Podem ser feitas em qualquer ordem, ou em
  paralelo por pessoas diferentes.
- **US4 depende da sub-fase 5A**: antes da reconciliação, `bg-card` resolve para
  transparente, então não há como estilizar o cartão corretamente.
- **5A bloqueia 5B e 5C** — é a dependência real que o `plan.md` aponta.

### Dentro das histórias

- T006 e T007 são independentes entre si; T008–T011 exigem ambas concluídas.
- T012 → T015 (o cursor precisa conhecer a nova estrutura de grid).
- T014 pode ser feita junto de T012, mas verificar só depois das duas.
- T020 → T021 → T022 são sequenciais (mesmo arquivo, mesma região).
- T023 é sequencial em relação a T022 (o rename só faz sentido com o novo
  mapeamento no lugar).
- T027/T028 bloqueiam T034–T037 (os consumidores precisam da primitiva).

## Parallel Execution Examples

**Linha de base (Phase 2)** — três medições independentes:

```
T003 (contenção) ‖ T004 (revelação) ‖ T005 (tokens + imagens)
```

**US1 verificação**:

```
T008 (kanban) ‖ T009 (scrum) ‖ T010 (rolagem manual)
```

**US2 verificação**:

```
T016 (métricas) ‖ T017 (markdown) ‖ T018 (rolagem manual + histórico)
```

**US3 sub-fase 5B** — arquivos distintos, sem dependência entre si:

```
T027 (select) ‖ T028 (input) ‖ T029 (card) ‖ T030 (table) ‖ T031 (skeleton) ‖ T032 (badge)
```

**US3 sub-fase 5C** — por área, arquivos distintos:

```
T034 (filtros) ‖ T035 (formulário) ‖ T036 (botões itsm) ‖ T038 (sidebar) ‖ T039 (topbar) ‖ T040 (composer) ‖ T041 (assistente)
```

T037 fica fora do paralelo acima por tocar o mesmo arquivo da US1 (`board.tsx`).

**Polish**:

```
T049 (tsc) ‖ T050 (eslint) ‖ T051 (deps) ‖ T053 (tokens)
```

## Implementation Strategy

### MVP (entrega mínima com valor)

**US1 sozinha** — T001 a T011. Fecha o defeito mais grave em aberto (a página
saindo dos limites e tirando a navegação da tela) com duas alterações de uma
linha cada, sem tocar em cor nenhuma. É a menor mudança com maior efeito
percebido e é reversível isoladamente.

### Incrementos seguintes

1. **US1 + US2** — os dois defeitos que a pessoa relatou estão fechados. Ainda
   sem risco global: nada de token foi tocado.
2. **+ US3-5A (tokens)** — ponto de maior risco da rodada, isolado num
   incremento próprio, com comparação visual de todas as telas (T026/T045) antes
   de seguir. Se algo regredir, o *revert* atinge só `globals.css` e o rename.
3. **+ US3-5B/5C (componentes)** — migração por área, cada fatia verificável.
4. **+ US4** — ajuste pontual, depende só de 5A.

### Nota de risco

A única tarefa com alcance global é T023 (79 renomeações). É mecânica e
verificável por `grep`, e o valor computado é idêntico antes e depois, então o
delta visual esperado é zero. Ainda assim, é o ponto onde a comparação com as
imagens de T005 importa mais.

---

## Adendo — pedidos posteriores (mesma rodada)

Itens pedidos depois do `/speckit-tasks`, implementados e verificados no
navegador. Ficam registrados aqui para o histórico da rodada não mentir sobre o
escopo executado.

- [X] A01 Criar `frontend/src/components/ui/alert-dialog.tsx` sobre `@base-ui/react/alert-dialog`, com `size` (`default`/`sm`), `AlertDialogMedia` e ação destrutiva
- [X] A02 Substituir os 3 `window.confirm` por AlertDialog: `itsm/reprocess-button.tsx`, `itsm/resolve-button.tsx` (submetem o form por `requestSubmit()`) e `shell/app-sidebar.tsx` (diálogo controlado por estado, porque o gatilho é item de menu de contexto)
- [X] A03 Criar `frontend/src/components/ui/dialog.tsx` (diálogo comum, com botão de fechar) — `AlertDialog` seria semanticamente errado para formulário
- [X] A04 Criar `frontend/src/components/itsm/new-ticket-dialog.tsx` e remover a rota `frontend/src/app/(shell)/itsm/new/` — criação de chamado passa a abrir em diálogo sobre `/itsm`
- [X] A05 Corrigir o alinhamento do popup do Select com `alignItemWithTrigger={false}` + `side="bottom"` + `align="start"` em `ui/select.tsx`; o padrão do Base UI sobrepõe o gatilho alinhando o item selecionado (estilo select nativo do macOS), o que deixava a lista torta
- [X] A06 Migrar o `<select>` de prioridade de `itsm/ticket-form.tsx` para o Select do produto — último `<select>` nativo do projeto
- [X] A07 Corrigir os tokens `--shadow-*` em `frontend/src/app/globals.css`: eram anéis sólidos `0 0 0 1px` numa rampa azulada de tema claro (`#3f424d`, `#595d6c`, `#9397ab`), mais claros que a própria superfície — daí a "borda branca feia" nos cartões e o anel quase branco nos diálogos. Passaram a usar branco com alfa (6%/8%/10%), no mesmo idioma de `--color-divider`
- [X] A08 Reescrever `ui/card.tsx` no formato shadcn (`data-slot` + `CardHeader`/`CardTitle`/`CardDescription`/`CardContent`/`CardFooter`), preservando o atalho `title`/`action` das 17 chamadas
- [X] A09 Criar `ui/badge.tsx` (cva + `data-slot`) com os 5 tons do antigo `Tag`, valores idênticos; migrar as 5 telas e remover `ui/tag.tsx`
- [X] A10 Reescrever `ui/skeleton.tsx` no formato shadcn (`data-slot`, `cn`, props de `div`)
- [X] A11 Migrar para `Button` os controles de `shell/topbar.tsx` e os 3 de `shell/app-sidebar.tsx` (fechar, colapsar, "Nova conversa")

### Não migrados por decisão (com motivo)

- `app-sidebar.tsx` linha ~145: sobreposição de fundo em tela cheia (`fixed inset-0`) que fecha o menu no mobile — é uma superfície de clique, não um botão de UI; `Button` traria altura/raio/estados que não fazem sentido.
- `app-sidebar.tsx` linha ~423: item de lista de conversa, com truncamento, estado ativo e ícone de favorito — as classes do `cva` do `Button` brigariam com o layout da linha sem ganho visual.
- `assistant/*` (`chat-composer`, `source-accordion`, `empty-state`, `conversation-view`): ficam sob `.v0-assistant`, que tem paleta própria (`--v0-*`) escopada desde a spec 003 e declarada intocada nesta rodada (I-05). Migrar exigiria decidir se o tema do Assistente converge para o do produto — decisão de escopo, não de implementação.
- [X] A12 Adicionar `sonner` + `ui/sonner.tsx` (`Toaster` dark-only, sem `next-themes`) e montar no `app/layout.tsx`
- [X] A13 Criar `lib/undoable.ts` — janela de desfazer que ADIA o efeito em vez de reverter (backend faz hard delete com CASCADE, não tem restore)
- [X] A14 Ligar toast+desfazer na exclusão de conversa (`shell/app-sidebar.tsx` + `lib/use-conversations.ts` ganham `removeLocally`/`restoreLocally`, injetáveis pelo Assistente) e no reprocessar (`itsm/reprocess-button.tsx`)

### SC-008 quebrado por pedido explícito

`sonner@2.0.7` é a **única** dependência nova da rodada, pedida nominalmente.
Contraria SC-008 ("nenhuma dependência nova") e a Constituição §V ("nenhuma
dependência nova onde o que já está instalado resolve") — `@base-ui/react`
exporta `toast`, que cobriria o caso sem pacote novo. Fica registrado como
decisão consciente, não como descuido. `next-themes` NÃO foi instalado: o
produto é dark-only, o `Toaster` fixa `theme="dark"`.

### Skeleton: medido, não havia timeout

Hipótese de "timeout no skeleton" não se confirmou. Medição de navegação
client-side (`MutationObserver`, dev-mode):

| navegação | skeleton visível | conteúdo |
|---|---|---|
| Home 1ª vez | 74 ms | 4263 ms |
| Agile | 33 ms | 334 ms |
| Home 2ª vez (compilada) | 38 ms | 337 ms |

Skeleton sempre entre 33 e 74 ms — não há atraso artificial em lugar nenhum, e
nenhum `loading.tsx` tem timer. Os 4.2 s da primeira visita são compilação
sob demanda do dev-server mais o cold start de `GET /api/v1/agile/sprint`
(3.4 s na primeira chamada, 1.4 ms nas seguintes; os demais endpoints
respondem em ~4 ms). Depois de compilado, 337 ms. Em `next build` a compilação
não existe. Nenhuma alteração feita — não havia o que remover.

**Melhoria possível, não feita (fora do pedido):** `(shell)/page.tsx` faz
`Promise.all` de 3 buscas e só então renderiza; o `agile/sprint` frio segura os
cartões de ITSM que já estão prontos. Separar em fronteiras de `Suspense` por
seção faria cada cartão pintar sozinho. Ganho pequeno com o servidor quente
(337 ms), por isso ficou como opção em vez de mudança especulativa.
