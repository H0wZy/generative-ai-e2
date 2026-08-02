# Feature Specification: Densidade visual dos KPIs e gráficos dos painéis

**Feature Branch**: `010-condensar-kpis-paineis`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "deixe as kpis/gráficos do painel com melhor visualização. atualmente ta meio zoado, grande demais, deixe mais 'condensadas', isso vale pro painel do itsm também."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Painel principal (ITSM+Ágil) mais denso (Priority: P1)

Como usuário abrindo o painel principal (tela inicial que combina
indicadores de ITSM e Ágil), quero ver mais informação de uma vez, com
cartões de indicador e gráficos ocupando menos espaço vertical/horizontal
cada, para não precisar rolar tanto nem sentir que a tela está
desproporcionalmente grande para o volume de dado exibido.

**Why this priority**: é a primeira tela vista ao abrir a aplicação — o
excesso de espaço em branco e o tamanho fixo dos gráficos hoje empurram
conteúdo para fora da área visível sem necessidade, inclusive em janelas ou
painéis estreitos (ex.: quando a aplicação é usada embutida numa área menor
da tela).

**Independent Test**: abrir o painel principal em uma resolução de desktop
comum e verificar que todos os quatro indicadores numéricos e os quatro
cartões de gráfico ficam visíveis com significativamente menos rolagem que
o comportamento atual, sem cortar texto nem sobrepor elementos.

**Acceptance Scenarios**:

1. **Given** o usuário abre o painel principal, **When** a tela termina de
   carregar, **Then** os cartões de indicador numérico (incidentes abertos,
   itens críticos, concluídos, cumprimento de SLA) aparecem visivelmente
   mais compactos que hoje (menos preenchimento interno, mesma
   legibilidade).
2. **Given** o painel principal exibe os gráficos de progresso do sprint,
   velocidade, carga por squad e volume por status, **When** renderizados
   lado a lado, **Then** cada gráfico ocupa uma área proporcional ao dado
   que representa, sem espaço vazio excessivo ao redor do desenho.
3. **Given** o painel é aberto numa janela ou área estreita (largura
   reduzida, ex. um painel lateral ou embutido), **When** os gráficos são
   renderizados, **Then** eles se ajustam ao espaço disponível sem
   necessidade de rolagem horizontal nem corte de conteúdo.

---

### User Story 2 - Painel do workspace Ágil mais denso (Priority: P1)

Como usuário do workspace Ágil, quero que a tela de painel do sprint
(indicadores, burndown, velocidade e bloqueios) siga a mesma densidade
visual condensada do painel principal, para ter uma experiência consistente
em vez de uma tela "normal" e outra "grande demais".

**Why this priority**: mesmo problema da User Story 1, em outra tela — sem
resolver aqui, a inconsistência entre os dois painéis fica evidente.

**Independent Test**: abrir o painel do workspace Ágil com um sprint ativo
e comparar a densidade visual (altura ocupada por cada indicador/gráfico)
com o painel principal — devem parecer parte do mesmo sistema de design.

**Acceptance Scenarios**:

1. **Given** o usuário abre o painel do workspace Ágil com sprint ativo,
   **When** a tela é renderizada, **Then** os quatro indicadores (dias
   restantes, pontos concluídos, escopo adicionado, bloqueios) usam o
   mesmo padrão compacto dos indicadores do painel principal.
2. **Given** o gráfico de burndown é exibido, **When** renderizado,
   **Then** ocupa uma altura proporcionalmente menor que a atual mantendo a
   curva e os eixos legíveis.
3. **Given** o gráfico de velocidade (barras) é exibido, **When**
   comparado ao gráfico de velocidade do painel principal, **Then** ambos
   têm a mesma densidade visual (mesma escala de espaçamento e tamanho de
   fonte).

---

### Edge Cases

- Painel exibido em janela muito estreita (ex. abaixo de 400px de largura,
  caso de uso embutido/widget): gráficos precisam permanecer legíveis e sem
  overflow horizontal, mesmo condensados.
- Indicador com valor "indisponível" (fonte de dados fora do ar): o cartão
  condensado continua comunicando claramente a indisponibilidade, sem que a
  redução de espaço corte a mensagem de erro/hint.
- Gráfico sem dado (ex. "nenhuma execução na fila", "sem histórico de
  velocidade"): o estado vazio continua legível dentro da área reduzida do
  cartão, sem parecer cortado.
- Usuário com zoom de página aumentado (acessibilidade): a densidade maior
  não pode fazer texto ficar ilegível ou sobreposto em zoom até 200%.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Os cartões de indicador numérico (KPI) do painel principal e
  do painel do workspace Ágil DEVEM usar um preenchimento interno reduzido
  em relação ao padrão atual, mantendo rótulo, valor e complemento (hint)
  legíveis.
- **FR-002**: Os gráficos de rosca (donut), barras e burndown DEVEM se
  redimensionar de forma proporcional ao espaço do cartão que os contém, em
  vez de usar dimensão fixa em pixels que ignora a largura disponível.
- **FR-003**: A grade de cartões de gráfico DEVE aproveitar melhor o
  espaço horizontal disponível em telas largas, sem deixar espaço vazio
  desproporcional entre um gráfico pequeno e a borda do cartão.
- **FR-004**: A densidade visual (espaçamento, tamanho de fonte, altura de
  gráfico) DEVE ser consistente entre o painel principal e o painel do
  workspace Ágil — o mesmo tipo de indicador (ex.: gráfico de barras de
  velocidade) DEVE parecer visualmente equivalente nas duas telas.
- **FR-005**: A redução de espaço NÃO PODE comprometer a legibilidade de
  texto nem cortar conteúdo em larguras de janela comuns (incluindo janelas
  estreitas, caso de uso embutido).
- **FR-006**: Estados de indicador indisponível ou gráfico sem dado
  DEVEM continuar totalmente legíveis dentro do novo layout condensado.

### Key Entities

- **Cartão de indicador (Stat)**: bloco com rótulo, valor numérico e
  complemento opcional.
- **Cartão de gráfico (Card + Donut/Bars/Burndown)**: bloco com título e
  uma visualização gráfica de dados agregados.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A altura total ocupada pela seção de indicadores numéricos do
  painel principal reduz em pelo menos 25% em relação ao layout atual,
  mantendo os mesmos quatro indicadores visíveis.
- **SC-002**: Em uma janela de 1280px de largura, todos os cartões de
  gráfico do painel principal ficam visíveis sem rolagem horizontal e com
  no máximo uma rolagem vertical curta (uma tela e meia, no máximo).
- **SC-003**: Testado em largura reduzida (ex. 380px, cenário de painel
  embutido), nenhum gráfico ultrapassa a borda do seu cartão nem força
  rolagem horizontal da página.
- **SC-004**: Comparando lado a lado um gráfico de velocidade do painel
  principal com o do painel Ágil, um usuário não percebe diferença de
  densidade/tamanho entre os dois.

## Assumptions

- "Painel do ITSM" citado pelo usuário se refere ao painel principal
  (`/`), que já combina indicadores de ITSM e Ágil na mesma tela (não há
  hoje uma tela de KPIs dedicada só a ITSM separada da fila de tickets) —
  esta spec cobre esse painel principal e o painel do workspace Ágil
  (`/agile`).
- A fila de tickets (`/itsm`, tabela de tickets) não tem cartões de
  KPI/gráfico hoje e fica fora do escopo desta spec — está coberta pelas
  specs de tradução (008) e de squads (012) quando aplicável.
- Redesenho de paleta de cores ou de tipo de gráfico (ex. trocar donut por
  barra) está fora de escopo — o pedido é de densidade/tamanho, não de
  mudança de linguagem visual.
- O caso "painel embutido em largura estreita" citado nos cenários reflete
  o uso relatado da aplicação dentro de um painel lateral menor que a tela
  cheia; o layout responsivo já existente é a base, esta spec ajusta a
  densidade dentro dele.
