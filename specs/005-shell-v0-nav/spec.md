# Feature Specification: Navegação do shell com ícones, colapso e largura estável

**Feature Branch**: `005-shell-v0-nav`

**Created**: 2026-08-01

**Status**: Draft

**Input**: User description: "Continuar a unificação visual com /assistant: a barra lateral do restante do produto (ITSM/Agile) ainda não tem ícones nem o botão de colapsar que a barra do Assistente já tem, e o usuário percebeu que a largura da barra lateral parece mudar dependendo da página principal renderizada (ex.: dashboard do ITSM) — comportamento que parece bug e precisa de diagnóstico e correção. Clonar o padrão visual e de interação da barra lateral do Assistente (ícones por item, botão de colapsar/expandir, larguras fixas expandida/colapsada) para a navegação principal do shell, mantendo o alternador de workspace e o selo 'em breve'. Fora de escopo: redesenho do conteúdo interno das páginas de ITSM/Agile além da herança de cor já feita na rodada anterior (004)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Barra lateral do shell ganha ícones e botão de colapsar iguais ao Assistente (Priority: P1)

Um usuário que navega entre o Assistente de IA e o restante do produto (ITSM/Agile) vê a mesma barra lateral — com ícone por item de menu e um botão para colapsar/expandir a barra — em vez de uma barra sem ícones e sem esse controle, que hoje faz o restante do produto parecer uma tela diferente colada na mesma navegação.

**Why this priority**: É a lacuna mais visível que sobrou da rodada anterior (004), que unificou só a cor de fundo/texto, não os elementos de navegação em si. Sem isso, a sensação de "duas telas diferentes" continua mesmo com a paleta já unificada.

**Independent Test**: Abrir `/assistant`, depois `/itsm` ou `/agile`, e confirmar visualmente que a barra lateral tem ícone ao lado de cada item de menu e o mesmo botão de colapsar/expandir presente nos dois lugares, sem depender de nenhuma outra tela estar pronta.

**Acceptance Scenarios**:

1. **Given** o usuário está em qualquer tela do shell (ITSM ou Agile), **When** ele olha para a barra lateral, **Then** cada item de navegação (Home, Dashboard, Assets, etc.) mostra um ícone reconhecível ao lado do rótulo, igual ao padrão já usado na barra do Assistente.
2. **Given** o usuário está em qualquer tela do shell em uma janela larga (desktop), **When** ele clica no botão de colapsar, **Then** a barra lateral encolhe para uma versão só com ícones (sem rótulo de texto), e ao clicar em expandir volta ao estado com rótulos, exatamente como acontece hoje na barra do Assistente.
3. **Given** a barra lateral está colapsada, **When** o usuário observa o alternador de workspace (ITSM/Agile) e o selo "em breve" nos itens não implementados, **Then** esses elementos continuam se comportando corretamente (escondendo texto redundante, sem quebrar layout).

---

### User Story 2 - Largura da barra lateral deixa de variar entre páginas (Priority: P2)

Um usuário que navega entre diferentes páginas do shell (por exemplo, do Dashboard do ITSM para o Backlog do Agile) vê a barra lateral sempre com a mesma largura, independentemente do que está sendo mostrado na área principal da tela.

**Why this priority**: É um bug relatado diretamente pelo usuário — a navegação parece "pular" ou ficar inconsistente de largura, o que compromete a credibilidade de qualquer polimento visual feito nas rodadas anteriores. Vem depois da US1 porque a correção faz mais sentido já sobre a barra lateral no formato novo (com ícones/colapso), evitando retrabalho duplo.

**Independent Test**: Medir (visualmente ou via inspeção) a largura da barra lateral em pelo menos três páginas com conteúdos principais bem diferentes (ex.: Dashboard do ITSM com tabela larga, Backlog do Agile, formulário de novo ticket) e confirmar que o valor é idêntico nas três, tanto no estado expandido quanto no colapsado.

**Acceptance Scenarios**:

1. **Given** o usuário está no Dashboard do ITSM (conteúdo principal largo, com tabela), **When** ele compara a largura da barra lateral com a de outra página do shell com conteúdo mais estreito, **Then** as duas larguras são idênticas.
2. **Given** o usuário redimensiona a janela do navegador para larguras diferentes (acima e abaixo do ponto de quebra mobile/desktop), **When** ele observa a barra lateral em cada página do shell, **Then** o comportamento responsivo (barra lateral vs. navegação compacta) é o mesmo em todas as páginas, sem depender do conteúdo principal renderizado.

---

### User Story 3 - Cabeçalho do shell casa visualmente com o cabeçalho do Assistente (Priority: P3)

Um usuário que troca entre o Assistente e o restante do produto vê um cabeçalho superior com a mesma altura, espaçamento e estilo de borda nos dois lugares, não apenas a barra lateral.

**Why this priority**: É um refinamento complementar às duas prioridades anteriores — sem ele a unificação fica "quase completa", mas o impacto percebido é menor que ícones/colapso (US1) ou o bug de largura (US2), por isso vem por último.

**Independent Test**: Abrir `/assistant` e qualquer página do shell lado a lado (ou em sequência) e comparar altura, espaçamento interno e borda inferior do cabeçalho superior — devem ser visualmente equivalentes.

**Acceptance Scenarios**:

1. **Given** o usuário está em qualquer página do shell, **When** ele observa o cabeçalho superior, **Then** a altura, o espaçamento e a borda inferior são visualmente equivalentes aos do cabeçalho do Assistente, mantendo a informação hoje exibida (seção ativa, workspace).

### Edge Cases

- Estado de colapso da barra lateral é local à sessão de navegação (não precisa persistir entre recarregamentos de página) — mesma regra já usada na barra do Assistente.
- Em telas estreitas (mobile), o comportamento de navegação compacta (fora do formato "barra lateral fixa") deve continuar funcionando para todos os itens de menu, incluindo os marcados "em breve", sem exigir o botão de colapsar (que é conceito só de tela larga).
- Itens de menu ainda não implementados (selo "em breve") mantêm o ícone visível tanto expandido quanto colapsado, só o rótulo de texto e o selo somem no colapsado.
- Link ativo (página atual) continua destacado visualmente em qualquer combinação de estado (expandido/colapsado, largura de janela).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A barra de navegação lateral do shell (ITSM/Agile) DEVE exibir um ícone reconhecível ao lado de cada item de menu, para todo item existente hoje (Home, Dashboard, Assets, Base de Conhecimento, Automações, Assistente de IA, Administração, Backlog, Quadro Scrum, Quadro Kanban).
- **FR-002**: A barra de navegação lateral do shell DEVE oferecer um controle de colapsar/expandir em telas largas (desktop), reduzindo a barra para uma versão compacta (só ícones) e restaurando a versão com rótulos de texto, sem perda de nenhum item de menu em nenhum dos dois estados.
- **FR-003**: A largura da barra de navegação lateral (tanto expandida quanto colapsada) DEVE ser idêntica em toda página do shell, independentemente do conteúdo renderizado na área principal da tela.
- **FR-004**: O comportamento responsivo da navegação (alternância entre barra lateral fixa em telas largas e navegação compacta em telas estreitas) DEVE ser consistente entre todas as páginas do shell.
- **FR-005**: O alternador de workspace (ITSM/Agile) e o selo "em breve" em itens não implementados DEVEM continuar funcionando corretamente em qualquer combinação de estado (expandido/colapsado, largura de janela), sem quebra visual ou perda de informação essencial (destino do link, indicação de "não implementado").
- **FR-006**: O destaque visual do item de menu correspondente à página atual DEVE continuar funcionando em qualquer estado da barra lateral (expandida ou colapsada).
- **FR-007**: O cabeçalho superior do shell DEVE ter altura, espaçamento interno e estilo de borda visualmente equivalentes aos do cabeçalho da tela do Assistente, preservando as informações hoje exibidas (seção ativa e workspace).
- **FR-008**: Toda mudança de cor de ícone e da barra lateral introduzida nesta rodada DEVE manter o mesmo nível de contraste (AA) já garantido pela paleta unificada na rodada anterior (004).

### Key Entities

- **Item de menu**: entrada de navegação do shell (rótulo, destino, ícone, se está implementado ou não); já existe hoje sem ícone associado.
- **Estado de colapso da barra lateral**: expandida (com rótulos) ou colapsada (só ícones); local à sessão de navegação, não persistido.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos itens de menu do shell (ITSM e Agile) exibem um ícone reconhecível, tanto na barra expandida quanto na colapsada.
- **SC-002**: A largura medida da barra lateral é idêntica (mesmo valor, sem variação) em pelo menos três páginas do shell com conteúdos principais distintos, tanto no estado expandido quanto no colapsado.
- **SC-003**: 0 casos de item de menu, alternador de workspace ou selo "em breve" quebrado ou ilegível em qualquer combinação de estado (colapso × largura de janela) testada.
- **SC-004**: 100% das combinações de texto/ícone sobre fundo introduzidas nesta rodada atendem contraste mínimo AA (4,5:1 texto de corpo, 3:1 texto grande/ícone), medido e não estimado.
- **SC-005**: Um usuário alternando entre o Assistente e qualquer página do shell não percebe diferença de altura, espaçamento ou borda no cabeçalho superior.

## Assumptions

- O padrão de ícones, colapso e largura fixa já validado na barra lateral do Assistente é a referência a ser replicada — não é necessário desenhar um padrão novo do zero.
- Rótulos, destinos e status "implementado/em breve" dos itens de menu não mudam nesta rodada — só a apresentação (ícone, comportamento de colapso, largura) é afetada.
- O ajuste fino do conteúdo interno de cada página de ITSM/Agile (tabelas, formulários, cards) continua fora de escopo, como já estabelecido na rodada 004 — esta rodada cobre apenas a casca de navegação (barra lateral e cabeçalho).
- A causa raiz da variação de largura relatada pelo usuário será diagnosticada durante o planejamento técnico (rodada de implementação); esta especificação garante o resultado observável (largura estável), não prescreve a causa.
