# Feature Specification: Quadro Ágil único e drag-and-drop confiável

**Feature Branch**: `009-consolidar-quadro-agil`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "as telas de agile tao mt ruins, parece que o quadro scrum é uma copia do quadro kanban. deixe apenas 'Quadro' (um quadro). arrume o drag and drop dele, ta muito bugado: quando pega uma task pra arrastar, pega a barra lateral junto + as outras tasks. melhore a visualização dos quadros jira (inclusive o drag and drop)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Um único Quadro no workspace Ágil (Priority: P1)

Como usuário do workspace Ágil, quero encontrar um único item "Quadro" na
navegação (em vez de "Quadro Scrum" e "Quadro Kanban" lado a lado), para não
achar que a aplicação duplicou a mesma tela por engano.

**Why this priority**: é o problema mais visível — duas rotas diferentes
renderizam o mesmo componente (`Board`) com a mesma aparência, mudando
apenas o filtro de escopo (sprint ativo vs. board completo). Isso lê como
bug de UI, não como duas features distintas.

**Independent Test**: abrir o workspace Ágil e verificar que existe apenas
um item de quadro na navegação; dentro dele, alternar entre "sprint atual" e
"board completo" deve ser possível sem sair da tela nem trocar de rota.

**Acceptance Scenarios**:

1. **Given** o usuário está no workspace Ágil, **When** olha a navegação de
   abas/seções, **Then** existe um único item "Quadro" (não "Quadro Scrum" e
   "Quadro Kanban" separados).
2. **Given** o usuário está na tela "Quadro", **When** alterna o escopo entre
   "sprint atual" e "todas as issues do board", **Then** a lista de colunas e
   cards é atualizada sem navegar para uma URL diferente nem recarregar a
   página inteira.
3. **Given** um usuário tinha um link salvo para a antiga rota do quadro
   Scrum ou Kanban, **When** acessa esse link, **Then** chega à tela
   "Quadro" (com o escopo correspondente pré-selecionado), em vez de ver
   página não encontrada.

---

### User Story 2 - Arrastar um card move só o card (Priority: P1)

Como usuário movendo um item entre colunas do quadro, quero que arrastar um
card afete apenas aquele card, para não ver a barra lateral e outros cards
"grudarem" no arrasto e a tela ficar com aparência quebrada.

**Why this priority**: bug funcional que compromete a única forma visual de
mover itens no quadro — o mecanismo de teclado (select) já existe como
alternativa, mas o drag-and-drop é a interação primária esperada num quadro
estilo Jira/Trello e hoje está visivelmente instável.

**Independent Test**: abrir o Quadro com pelo menos duas colunas com cards,
iniciar o arrasto de um card e observar que somente aquele card acompanha o
cursor — a barra lateral, o cabeçalho e os demais cards permanecem parados
em seus lugares durante toda a operação.

**Acceptance Scenarios**:

1. **Given** o Quadro tem cards em pelo menos duas colunas, **When** o
   usuário pressiona e arrasta um card, **Then** apenas esse card exibe
   feedback visual de arrasto (segue o cursor / fica com opacidade ou
   sombra de "sendo movido"); nenhum outro elemento da tela (barra lateral,
   outros cards, cabeçalho de coluna) se desloca ou pisca.
2. **Given** um card está sendo arrastado, **When** o usuário o solta sobre
   uma coluna válida, **Then** o card se move para essa coluna e o restante
   do layout permanece estável (sem sobreposição residual).
3. **Given** um card está sendo arrastado, **When** o usuário solta fora de
   qualquer coluna (ou aperta Esc, se suportado pelo navegador), **Then** o
   card retorna à coluna de origem sem deixar artefato visual.
4. **Given** o usuário está usando teclado/leitor de tela, **When** aciona o
   seletor "Mover para outra coluna" de um card, **Then** a movimentação
   funciona exatamente como hoje — o drag-and-drop é aprimorado sem remover
   esse caminho alternativo já existente.

---

### User Story 3 - Visual do quadro mais próximo do Jira (Priority: P2)

Como usuário acostumado com quadros estilo Jira, quero que colunas, cards e
o estado de arrasto tenham uma apresentação mais clara (bordas de coluna
definidas, indicação de onde o card vai cair, card "fantasma" no lugar de
origem durante o arrasto), para entender de forma imediata o estado do
quadro sem precisar interpretar uma interface confusa.

**Why this priority**: melhoria de percepção/usabilidade que depende da
correção do bug (User Story 2) já ter deixado o mecanismo de arrasto
estável — é o polimento em cima da correção funcional.

**Independent Test**: comparar visualmente o Quadro antes/depois — colunas
com contorno e cabeçalho legíveis, coluna de destino destacada durante o
arrasto (drag-over), card de origem com aparência "esvaziada"/fantasma
enquanto arrastado.

**Acceptance Scenarios**:

1. **Given** o usuário arrasta um card sobre uma coluna candidata, **When**
   o cursor passa sobre essa coluna, **Then** a coluna exibe um indicador
   visual claro de "soltar aqui" (borda ou fundo destacado), distinto do
   indicador atual de "limite de WIP estourado".
2. **Given** um card está sendo arrastado, **When** observado no lugar de
   origem, **Then** o espaço do card na coluna de origem fica visualmente
   indicado como vazio/fantasma até o solte, em vez de simplesmente
   desaparecer ou duplicar.
3. **Given** o quadro tem várias colunas, **When** renderizado em tela
   cheia, **Then** cada coluna tem largura, espaçamento e contraste de
   borda suficientes para diferenciar visualmente uma coluna da outra sem
   depender só da cor de fundo.

---

### Edge Cases

- Arrasto iniciado e o mouse sai da janela do navegador antes de soltar:
  o card deve retornar à coluna de origem, sem ficar "preso" em estado de
  arrasto.
- Coluna de destino está com o limite de WIP estourado: o indicdor de
  drag-over não deve ser confundido com o aviso de WIP — ambos podem
  coexistir, mas precisam ser visualmente distinguíveis.
- Usuário solta o card na mesma coluna de origem: nenhuma requisição de
  transição é feita (comportamento hoje já correto em `board.tsx`, deve ser
  preservado).
- Board vazio (nenhuma coluna ou nenhum card): quadro único continua
  exibindo o estado vazio já existente, sem referência a "Scrum" ou
  "Kanban" no texto.
- Alternância de escopo (sprint atual vs. board completo) enquanto um
  arrasto está em andamento: o arrasto em andamento deve ser cancelado ou
  a troca de escopo bloqueada até a operação terminar, para não deixar o
  card em estado inconsistente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O workspace Ágil DEVE expor um único item de navegação para o
  quadro ("Quadro"), substituindo os itens separados "Quadro Scrum" e
  "Quadro Kanban".
- **FR-002**: A tela "Quadro" DEVE permitir alternar entre o escopo "sprint
  atual" e "todas as issues do board" sem navegação de página inteira,
  preservando os dois modos de consulta que existem hoje.
- **FR-003**: Links existentes para as antigas rotas do quadro Scrum e do
  quadro Kanban DEVEM continuar funcionando, redirecionando para a tela
  "Quadro" com o escopo equivalente pré-selecionado.
- **FR-004**: Durante o arrasto de um card, nenhum outro elemento da
  interface (barra lateral, outros cards, cabeçalhos de coluna) PODE se
  mover, piscar ou sobrepor de forma não intencional.
- **FR-005**: O arrasto DEVE mover exclusivamente o card de origem para a
  coluna de destino ao ser solto sobre uma coluna válida.
- **FR-006**: Soltar um card fora de uma área de coluna válida DEVE
  cancelar o arrasto e manter o card na coluna de origem, sem chamada de
  transição.
- **FR-007**: A coluna sob o cursor durante um arrasto ativo DEVE exibir um
  indicador visual de destino, distinto do indicador de limite de WIP
  estourado.
- **FR-008**: O caminho alternativo de mover um card via seletor
  (acessível por teclado) DEVE continuar funcionando sem alteração de
  comportamento.
- **FR-009**: O texto de estados vazios, cabeçalhos e mensagens da tela
  "Quadro" NÃO PODE referenciar "Scrum" ou "Kanban" como se fossem telas
  distintas — a distinção correta é o escopo selecionado.

### Key Entities

- **Quadro (Board)**: coleção de colunas com cards, com um escopo ativo
  (sprint atual ou board completo) que determina quais issues aparecem.
- **Card (WorkItem)**: item individual do quadro, pertence a uma coluna,
  pode estar em estado "sendo arrastado".
- **Coluna (BoardColumn)**: agrupador de cards por status, pode estar em
  estado "destino de arrasto ativo" e/ou "limite de WIP estourado".

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A navegação do workspace Ágil mostra exatamente um item de
  quadro, não dois.
- **SC-002**: Em 10 tentativas de arrastar um card em diferentes
  navegadores/dispositivos de teste, 0 delas produzem deslocamento visual
  de elementos fora do card arrastado.
- **SC-003**: 100% dos links para as rotas antigas de quadro Scrum/Kanban
  continuam levando a uma tela funcional de quadro.
- **SC-004**: Usuários conseguem identificar, sem instrução prévia, sobre
  qual coluna um card será solto durante o arrasto (indicador visual
  presente e perceptível).

## Assumptions

- A distinção funcional entre "sprint atual" e "board completo" continua
  existindo — não é removida, apenas deixa de ser duas rotas/abas para virar
  um controle (toggle/filtro) dentro de uma única tela.
- O mecanismo de movimentação via seletor acessível por teclado (já
  existente em `board.tsx`) é mantido como está — esta spec cobre a
  experiência de arrasto por mouse/touch e a consolidação de rota, não
  substitui o caminho acessível.
- O bug relatado (barra lateral e outros cards "grudando" no arrasto) é uma
  falha de isolamento visual do drag nativo do navegador — a causa raiz
  exata (empilhamento/z-index, imagem de arrasto, ou containment de
  layout) é investigada na fase de planejamento técnico, não nesta spec.
- Fora de escopo: reordenar cards dentro da mesma coluna por drag (hoje não
  existe e não foi pedido); suporte a swimlanes adicionais.
