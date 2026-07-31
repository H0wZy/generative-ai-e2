# Feature Specification: Unificação visual v0 — fundação de tokens + shell

**Feature Branch**: `004-v0-theme-shell`

**Created**: 2026-07-31

**Status**: Draft

**Input**: User description: "Replicar design visual da tela /assistant (shadcn + paleta near-black #141414 + branco elegante, tokens v0-*) para resto do frontend (shell: sidebar/topbar/workspace-switcher, depois ITSM, depois Agile). Rodada 1 escopo: fundação de tokens (trocar valores de --color-* em :root para paleta v0, dark-only, remover toggle claro/escuro e ThemeToggle) + shell (sidebar, topbar, workspace-switcher). Componentes ui/* (button, card, table, tag, stat, skeleton, empty-state, error-state, unavailable-state) já usam só classes semânticas de token, sem cor hardcoded, então herdam a paleta nova sem mudança de JSX. Mapear tokens que existem no v0 mas não no ink/brass atual (card, popover, ring, input, destructive) como novas variantes --color-* na mesma convenção. Manter fonte Inter no resto do app (v0 usa Geist só no /assistant). Efeito colateral aceito: trocar valor de token global recolore toda página que consome esses tokens (ITSM, Agile, em-construcao) imediatamente, mesmo que o ajuste fino de cada tela fique para rodadas seguintes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navegação visualmente coesa entre Assistente e resto do produto (Priority: P1)

Um usuário que abre o Assistente de IA e depois navega para ITSM ou Agile (ou vice-versa) percebe uma única identidade visual — fundo escuro elegante, superfícies e texto consistentes — em vez de duas experiências visuais diferentes coexistindo no mesmo produto.

**Why this priority**: É o motivo central do pedido — hoje o Assistente tem uma identidade visual própria (shadcn/v0, near-black) enquanto o restante do app usa um tema ink/brass separado. Essa divergência é o problema mais visível para qualquer usuário que circula entre as duas áreas.

**Independent Test**: Abrir `/assistant`, depois navegar para `/itsm` ou `/agile` (ou tela inicial do shell) e confirmar visualmente que fundo, texto e superfícies dos elementos de navegação (barra lateral, cabeçalho, alternador de workspace) usam a mesma paleta escura, sem precisar de nenhuma outra tela estar pronta.

**Acceptance Scenarios**:

1. **Given** o usuário está em `/assistant` com o visual near-black atual, **When** ele clica em um link para ITSM ou Agile, **Then** a barra lateral e o cabeçalho do restante do app aparecem com fundo e texto na mesma paleta escura do Assistente, sem qualquer tela de transição clara.
2. **Given** o usuário carrega o app pela primeira vez em qualquer rota (não só `/assistant`), **When** a página termina de carregar, **Then** não há nenhum instante de tema claro visível antes do escuro (sem "flash" de tema).

---

### User Story 2 - Fim da alternância de tema claro/escuro (Priority: P2)

Um usuário não encontra mais em nenhuma tela do produto um controle para trocar entre tema claro e escuro — o produto passa a ter uma única aparência, a escura, em todo lugar.

**Why this priority**: Consequência direta da decisão de tornar o produto dark-only, para bater exatamente com o Assistente (que não tem variante clara). É menos crítico que a US1 porque é uma remoção, não uma nova capacidade percebida ativamente — mas precisa ser verificável para não sobrar um controle morto ou quebrado na tela.

**Independent Test**: Percorrer cada tela que hoje expõe o alternador de tema (cabeçalho do shell) e confirmar que o controle não existe mais, sem depender de nenhuma outra rodada de trabalho.

**Acceptance Scenarios**:

1. **Given** o usuário está em qualquer tela do shell (ITSM ou Agile), **When** ele observa o cabeçalho, **Then** não há botão ou controle de alternância de tema claro/escuro.
2. **Given** um usuário que já tinha escolhido tema claro em uma visita anterior, **When** ele volta ao produto após esta mudança, **Then** ele vê o tema escuro (não há mais tema claro para carregar), sem erro ou tela quebrada.

---

### User Story 3 - Componentes compartilhados herdam a nova paleta sem retrabalho tela a tela (Priority: P3)

Um usuário que usa cartões, tabelas, badges, estados vazios/erro/indisponível em qualquer tela do produto (não só as que forem manualmente ajustadas nesta rodada) já os vê na paleta escura nova, com legibilidade preservada.

**Why this priority**: É o que dá alcance à mudança sem exigir retrabalho tela a tela imediatamente — importante para o valor da entrega, mas é consequência técnica das duas prioridades anteriores, não um objetivo em si; o ajuste fino específico de cada tela (ITSM, Agile) é propositalmente uma rodada futura.

**Independent Test**: Abrir qualquer tela existente que use cartões, tabelas, badges ou estados vazios/erro (por exemplo, listagem de ITSM) sem que ela tenha sido tocada nesta rodada, e confirmar que esses elementos já aparecem na paleta escura nova, com texto legível.

**Acceptance Scenarios**:

1. **Given** uma tela de ITSM ou Agile que não foi diretamente modificada nesta rodada, **When** o usuário a visualiza após a mudança, **Then** cartões, tabelas, badges e estados (vazio/erro/indisponível) aparecem na paleta escura nova, com contraste de texto preservado.
2. **Given** uma tela ainda "em construção" (placeholder), **When** o usuário a visualiza, **Then** ela também reflete a paleta escura nova, sem sobra visual do tema antigo.

### Edge Cases

- Usuário com tema claro salvo de uma visita anterior: ao remover a alternância, o produto deve simplesmente carregar no escuro, sem depender do valor salvo anteriormente e sem erro de carregamento.
- Tela que hoje depende de um valor de cor que não existe na paleta nova (ex.: variantes de superfície elevada, contorno de foco, campo de formulário, cor de ação destrutiva): a tela não pode ficar com um elemento sem cor definida (transparente/quebrado) — a paleta nova precisa cobrir todo valor de cor hoje em uso antes da mudança.
- Elementos de navegação que sinalizam estado (link ativo, selo "em breve", contorno de foco de teclado) continuam se comportando exatamente como hoje — só a aparência de cor muda, não a lógica de quando aparecem.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A barra de navegação lateral, o cabeçalho e o alternador de workspace do restante do produto DEVEM usar a mesma paleta visual escura (fundo quase preto, texto branco elegante, superfícies arredondadas) já usada na tela do Assistente de IA.
- **FR-002**: O produto NÃO DEVE mais oferecer nenhum controle de alternância entre tema claro e escuro, em nenhuma tela.
- **FR-003**: O produto DEVE renderizar exclusivamente no tema escuro em toda tela, desde o primeiro carregamento, sem instante visível de tema claro.
- **FR-004**: Elementos de interface compartilhados entre todas as telas (cartões, tabelas, badges, botões, indicadores estatísticos, estados vazio/erro/indisponível) DEVEM adotar a paleta escura nova automaticamente, sem exigir alteração individual de cada tela que os usa.
- **FR-005**: Toda combinação de texto sobre fundo na paleta nova DEVE manter pelo menos o mesmo nível de contraste (AA) já garantido no tema anterior, mantendo a legibilidade em qualquer tela do produto.
- **FR-006**: A paleta visual nova DEVE cobrir todo valor de cor hoje em uso pelo produto (incluindo os usados por navegação, cartões, formulários, foco de teclado e estados de erro/perigo), de forma que nenhum elemento existente fique sem cor definida após a mudança.
- **FR-007**: O comportamento funcional da navegação (destaque de link ativo, selo "em breve" em itens não implementados, indicador visível de foco de teclado) DEVE permanecer o mesmo de hoje — a mudança é apenas de aparência, não de comportamento.
- **FR-008**: A família tipográfica usada fora da tela do Assistente de IA NÃO DEVE mudar nesta rodada.
- **FR-009**: Toda tela do produto que hoje consome a paleta de cores global (incluindo telas de ITSM, Agile e placeholders "em construção" ainda não ajustadas visualmente nesta rodada) DEVE refletir a paleta escura nova imediatamente, mesmo antes de receber ajuste fino de layout em rodadas futuras.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das telas do produto (Assistente, ITSM, Agile, placeholders) carregam no tema escuro no primeiro acesso, sem nenhum instante de tema claro visível.
- **SC-002**: Zero controles de alternância de tema claro/escuro permanecem acessíveis em qualquer tela do produto.
- **SC-003**: 100% das combinações de texto sobre fundo usadas pelos elementos compartilhados (cartões, tabelas, badges, estados vazio/erro/indisponível, navegação) atendem contraste mínimo AA (4,5:1 para texto de corpo, 3:1 para texto grande/componentes de interface), medido e não estimado.
- **SC-004**: Um usuário navegando entre a tela do Assistente e qualquer outra tela do produto não percebe nenhuma mudança abrupta de cor de fundo ou de texto ao trocar de tela.
- **SC-005**: Nenhum elemento visual existente (navegação, cartão, tabela, badge, campo de formulário, foco de teclado, estado de erro) fica sem cor definida (transparente ou quebrado) após a mudança de paleta.

## Assumptions

- A organização optou por padronizar o produto inteiro no tema escuro; não há expectativa de reintroduzir um tema claro nesta ou em rodadas futuras.
- O ajuste fino específico de cada tela de ITSM e Agile (espaçamento, bordas, hierarquia visual particular de cada uma) fica para rodadas seguintes, dedicadas a cada área — esta rodada garante que a base de cor já muda em todo lugar, não que cada tela receba refino individual.
- A tela do Assistente de IA em si não muda nesta rodada — ela é a referência visual que o restante do produto passa a seguir.
- Preferência de tema anteriormente salva pelo usuário deixa de ter efeito, já que passa a existir apenas uma opção (escura); não é necessário migrar ou avisar sobre o valor salvo anteriormente.
- Os elementos de interface compartilhados (cartões, tabelas, badges, estados vazio/erro/indisponível, botões) já são construídos de forma a herdar paleta de cor centralizada, sem cor fixa individual — por isso conseguem adotar a paleta nova sem alteração própria.
