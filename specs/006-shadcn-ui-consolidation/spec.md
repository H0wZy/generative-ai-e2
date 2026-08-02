# Feature Specification: Consolidação de UI em shadcn e correção de scroll/reveal

**Feature Branch**: `006-shadcn-ui-consolidation`

**Created**: 2026-08-01

**Status**: Completed

**Input**: User description: "Round 006: corrigir scroll da página escapando limites no Kanban, corrigir salto brusco do typewriter no assistente com histórico, migrar componentes restantes para shadcn (selects, botões, cards, scroll areas) mantendo o design atual, e trocar o Link-como-botão 'Novo chamado' do /itsm por um card"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Quadro nunca escapa dos limites da tela (Priority: P1)

Ao abrir o Quadro Kanban (ou o Quadro Scrum), a pessoa vê o quadro ocupando
exatamente a área útil da janela. Só existe um scroll por eixo e ele pertence à
região correta: colunas rolam verticalmente dentro delas mesmas, o conjunto de
colunas rola horizontalmente dentro da faixa do quadro. A página em si não rola —
a barra lateral, o cabeçalho e as abas permanecem fixos e visíveis o tempo todo.

**Why this priority**: É o defeito mais grave em aberto. Hoje a página inteira
desce para fora dos limites, tirando a navegação da tela e criando uma segunda
barra de rolagem que compete com a das colunas. Torna o quadro desagradável de
usar e quebra a percepção de aplicação (parece um documento solto).

**Independent Test**: Abrir o Quadro Kanban em uma janela baixa o suficiente para
que uma coluna tenha mais cartões do que cabe na tela. Verificar que a área
rolável do documento é igual à altura da janela e que rolar com a roda do mouse
sobre uma coluna move apenas aquela coluna.

**Acceptance Scenarios**:

1. **Given** o Quadro Kanban aberto numa janela cuja altura é menor que o
   conteúdo da coluna mais cheia, **When** a página termina de carregar,
   **Then** o documento não apresenta barra de rolagem vertical própria e a
   barra lateral permanece inteiramente visível.
2. **Given** o Quadro Kanban aberto, **When** a pessoa rola sobre uma coluna até
   o último cartão, **Then** apenas o conteúdo daquela coluna se move; cabeçalho,
   abas e barra lateral permanecem no lugar.
3. **Given** o Quadro Scrum aberto (mesma estrutura de quadro), **When** o
   conteúdo excede a altura da janela, **Then** o comportamento é idêntico ao do
   Kanban.
4. **Given** qualquer página do shell, **When** o conteúdo é menor que a janela,
   **Then** nenhuma barra de rolagem extra aparece.

---

### User Story 2 - Resposta aparece progressivamente sem solavanco (Priority: P2)

Numa conversa que já tem histórico acima, a pessoa envia uma pergunta. A pergunta
fica ancorada no topo da área de leitura e a resposta se revela progressivamente
logo abaixo, como se estivesse sendo digitada, já formatada. Em nenhum momento a
conversa salta para outro ponto, pisca ou "sobe" sozinha.

**Why this priority**: O efeito de digitação existe e a formatação já é aplicada
durante a revelação, mas a transição continua causando um salto visível: no
instante em que a resposta começa, a conversa pula para o topo do histórico e
volta. Isso desorienta e faz a pessoa perder o ponto de leitura. É percepção de
qualidade, não bloqueio de uso — por isso vem depois da US1.

**Independent Test**: Abrir uma conversa longa (com rolagem), enviar uma
pergunta e observar a posição de leitura desde o envio até o fim da revelação.
A posição deve variar de forma monotônica e suave, nunca voltando ao início.

**Acceptance Scenarios**:

1. **Given** uma conversa com histórico suficiente para rolar, **When** a
   resposta começa a ser revelada, **Then** a posição de leitura não retorna ao
   topo da conversa em nenhum quadro da animação.
2. **Given** a resposta sendo revelada, **When** o texto cresce, **Then** o
   conteúdo já revelado não muda de posição nem é reformatado (sem refluxo).
3. **Given** a resposta sendo revelada, **When** a pessoa rola manualmente para
   ler o histórico acima, **Then** a revelação continua sem puxar a tela de volta.
4. **Given** uma conversa aberta a partir do histórico (mensagem antiga),
   **When** ela é carregada, **Then** nenhuma animação de digitação ocorre e o
   conteúdo aparece completo e formatado de imediato.

---

### User Story 3 - Controles com aparência e comportamento uniformes (Priority: P3)

Todos os controles interativos do produto — campos de seleção, botões, campos de
texto, painéis roláveis, cartões, tabelas e etiquetas — têm a mesma linguagem
visual, os mesmos estados (repouso, foco, hover, pressionado, desabilitado) e o
mesmo comportamento de teclado, em qualquer página. Nenhum controle aparece com
o visual padrão do sistema operacional destoando do restante.

**Why this priority**: Hoje há duas gerações de componentes convivendo: alguns
controles usam a biblioteca de componentes adotada, outros são marcação bruta
com estilo aplicado à mão. Os campos de seleção do quadro e dos filtros de
ticket renderizam com o widget nativo do sistema, que ignora o tema. Não impede
o uso, mas é o que mais destoa visualmente.

**Independent Test**: Percorrer as telas (Home, ITSM, Agile e suas abas,
Assistente) comparando cada tipo de controle. Todo controle do mesmo tipo deve
ser visualmente idêntico entre telas e operável só com teclado.

**Acceptance Scenarios**:

1. **Given** qualquer campo de seleção do produto, **When** ele é aberto,
   **Then** a lista de opções segue o tema do produto (não o widget nativo do
   sistema) e é navegável por teclado com indicação clara da opção em foco.
2. **Given** qualquer botão do produto, **When** comparado a outro botão de
   mesma hierarquia em outra tela, **Then** ambos têm altura, raio, tipografia e
   estados idênticos.
3. **Given** um painel rolável, **When** ele tem conteúdo excedente, **Then** a
   barra de rolagem tem a mesma aparência discreta usada no Assistente.
4. **Given** a migração concluída, **When** o produto é comparado ao estado
   anterior, **Then** a paleta, o espaçamento e a densidade permanecem os mesmos
   (a mudança é de implementação e consistência, não de identidade visual).
5. **Given** qualquer controle interativo, **When** navegado por teclado,
   **Then** há anel de foco visível e a ordem de tabulação segue a ordem visual.

---

### User Story 4 - Entrada para "Novo chamado" deixa de ser um bloco branco (Priority: P3)

Na fila de tickets, a ação de abrir um novo chamado é apresentada como um cartão
de ação coerente com os demais blocos da interface, em vez de um botão sólido de
alto contraste que domina a tela.

**Why this priority**: O elemento atual é um link estilizado como botão com
fundo da cor primária; no tema escuro isso resulta num retângulo branco que
puxa toda a atenção e destoa do restante. Ajuste pontual de aparência, sem
impacto funcional.

**Independent Test**: Abrir a fila de tickets e confirmar que a ação continua
alcançável por clique e por teclado, leva à criação de chamado, e não é mais o
elemento de maior contraste da tela.

**Acceptance Scenarios**:

1. **Given** a fila de tickets, **When** a pessoa observa a tela, **Then** a
   entrada para novo chamado se apresenta como superfície de cartão coerente com
   os demais blocos, sem preenchimento sólido de alto contraste.
2. **Given** a entrada para novo chamado, **When** acionada por clique ou por
   teclado, **Then** leva à tela de criação de chamado.
3. **Given** a entrada para novo chamado, **When** navegada por teclado,
   **Then** recebe foco visível e é anunciada como um link/ação com destino
   compreensível.

---

### Edge Cases

- Janela muito baixa (ex.: 600px de altura) com coluna de quadro muito cheia: o
  quadro continua contido; a coluna rola internamente.
- Coluna de quadro vazia: não gera área rolável nem altera a altura do quadro.
- Resposta do assistente muito curta (cabe inteira na tela): revelação ocorre sem
  qualquer movimento de rolagem.
- Resposta do assistente muito longa (várias telas): a pergunta permanece
  ancorada e a pessoa rola por conta própria; a revelação não sequestra a rolagem.
- Pessoa troca de conversa no meio de uma revelação: a revelação da conversa
  anterior não afeta a posição de leitura da nova.
- Preferência de "movimento reduzido" ativa: a revelação progressiva é suprimida
  e a resposta aparece completa de imediato.
- Campo de seleção com muitas opções (mais colunas que o normal): a lista rola
  dentro de si mesma sem empurrar o layout.
- Uso apenas por teclado, sem mouse: toda ação do quadro (incluindo mover cartão
  entre colunas) permanece possível.

## Requirements *(mandatory)*

### Functional Requirements

**Contenção de layout e rolagem**

- **FR-001**: A área rolável do documento MUST ser igual à área visível da
  janela em todas as telas do shell — nenhuma página pode gerar rolagem do
  documento inteiro.
- **FR-002**: Nenhum elemento auxiliar destinado apenas a leitores de tela pode
  aumentar a área rolável do documento.
- **FR-003**: Em telas de quadro, a rolagem vertical MUST pertencer à coluna e a
  rolagem horizontal MUST pertencer à faixa de colunas; não pode haver uma
  terceira região rolável englobando ambas.
- **FR-004**: Barra lateral, cabeçalho e abas MUST permanecer visíveis
  independentemente do volume de conteúdo da página.
- **FR-005**: Toda barra de rolagem visível no produto MUST ter a mesma
  aparência discreta, em qualquer região e em qualquer página.

**Revelação progressiva da resposta**

- **FR-006**: A resposta do assistente MUST ser revelada progressivamente,
  transmitindo a sensação de digitação.
- **FR-007**: Durante toda a revelação, o conteúdo já visível MUST estar
  formatado em sua apresentação final (títulos, listas, ênfase, código e tabelas)
   — não pode haver troca de apresentação ao terminar.
- **FR-008**: A revelação MUST NOT provocar mudança de posição do conteúdo já
  revelado (sem refluxo, sem colapso e sem recomposição da altura do conteúdo).
- **FR-009**: A posição de leitura MUST NOT retornar ao início da conversa em
  nenhum momento entre o envio da pergunta e o fim da revelação.
- **FR-010**: Se a pessoa rolar manualmente durante a revelação, o sistema MUST
  respeitar essa posição e não forçar retorno.
- **FR-011**: Mensagens carregadas do histórico MUST aparecer completas e
  formatadas, sem animação de revelação.
- **FR-012**: Com preferência de movimento reduzido ativa, a revelação
  progressiva MUST ser suprimida.

**Uniformidade dos controles**

- **FR-013**: Campos de seleção, botões, campos de texto, painéis roláveis,
  cartões, tabelas e etiquetas MUST usar a biblioteca de componentes já adotada
  pelo projeto, substituindo as implementações feitas à mão.
- **FR-014**: Campos de seleção MUST renderizar com o tema do produto e não com
  o widget nativo do sistema operacional.
- **FR-015**: A migração MUST preservar a identidade visual atual — paleta,
  espaçamento, raio de canto, tipografia e densidade permanecem os mesmos.
- **FR-016**: Todo controle interativo MUST ter anel de foco visível e ordem de
  tabulação coerente com a ordem visual.
- **FR-017**: Todo controle interativo MUST expor os mesmos estados visuais
  (repouso, hover, foco, pressionado, desabilitado) em todas as telas.
- **FR-018**: A alternativa por teclado para mover cartão entre colunas MUST
  continuar funcionando após a migração dos campos de seleção.
- **FR-019**: A migração MUST NOT introduzir dependência nova quando a
  biblioteca já instalada resolve o caso.

**Entrada de novo chamado**

- **FR-020**: A entrada para criar novo chamado MUST ser apresentada como
  superfície de cartão, sem preenchimento sólido de alto contraste.
- **FR-021**: A entrada para criar novo chamado MUST permanecer acionável por
  clique e por teclado e MUST levar à tela de criação de chamado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Em todas as telas do shell, a altura rolável do documento é igual à
  altura visível da janela (diferença de 0 pixel), verificado em pelo menos três
  alturas de janela distintas, incluindo uma menor que o conteúdo.
- **SC-002**: No Quadro Kanban e no Quadro Scrum existe no máximo uma região
  rolável por eixo, e a barra lateral permanece 100% visível em qualquer posição
  de rolagem.
- **SC-003**: Entre o envio da pergunta e o fim da revelação, a posição de
  leitura nunca assume um valor menor que o do quadro anterior por causa do
  sistema (nenhum retrocesso não solicitado), medido quadro a quadro.
- **SC-004**: Durante a revelação, a altura total do conteúdo é monotonicamente
  não decrescente — nunca encolhe.
- **SC-005**: 100% dos campos de seleção do produto abrem com a lista de opções
  no tema do produto; nenhum widget nativo do sistema permanece.
- **SC-006**: 100% dos controles interativos do produto são alcançáveis e
  operáveis por teclado, com foco visível.
- **SC-007**: Comparação visual antes/depois das telas migradas não apresenta
  mudança de paleta, espaçamento ou densidade — apenas de consistência.
- **SC-008**: Nenhuma dependência nova é adicionada ao projeto para concluir a
  migração.
- **SC-009**: A verificação de tipos e o linter permanecem sem erros novos em
  relação ao estado anterior à mudança.

## Assumptions

- **A-001**: "Migrar tudo para shadcn" significa migrar o que a biblioteca de
  componentes já adotada cobre. Componentes de domínio sem equivalente direto
  (indicadores, gráficos, estados vazios/indisponíveis, bolhas de mensagem)
  permanecem próprios, mas passam a se apoiar nas primitivas migradas.
- **A-002**: A biblioteca já instalada cobre seleção, painel rolável, campo de
  texto, separador, abas e afins; portanto a migração não exige dependência
  nova. Isso atende à Constituição §V (nenhuma dependência nova onde o
  instalado resolve).
- **A-003**: Painéis roláveis só passam a usar o componente de área rolável da
  biblioteca onde o conteúdo é passivo. Onde a rolagem convive com arrastar e
  soltar (colunas do quadro), a rolagem nativa é mantida e apenas a aparência da
  barra é padronizada — trocar por rolagem controlada por script arriscaria
  regredir o arrastar e soltar sem ganho visual, já que a aparência é a mesma.
- **A-004**: "Card" para a entrada de novo chamado significa uma superfície de
  cartão clicável coerente com os demais blocos do painel, mantendo a ação como
  um link real (navegação, não formulário).
- **A-005**: O efeito de digitação é puramente de apresentação: a resposta chega
  inteira do servidor e é revelada no cliente. Não há streaming token a token
  vindo do backend nesta rodada.
- **A-006**: A identidade visual de referência é a estabelecida nas rodadas 004 e
  005; nenhuma decisão desta rodada redefine paleta ou tipografia.

## Dependencies

- **D-001**: Depende da unificação de tokens semânticos concluída na rodada 004 —
  a migração se apoia nesses tokens para preservar a aparência.
- **D-002**: Depende da barra lateral única e do shell consolidados na rodada
  005.

## Out of Scope

- Streaming real de resposta token a token vindo do backend.
- Redesenho de identidade visual (paleta, tipografia, densidade).
- Migração de gráficos para biblioteca de terceiros.
- Correção do aviso de hidratação observado na tela do Assistente quando o
  workspace persistido difere do renderizado no servidor (defeito pré-existente,
  registrado para rodada futura).
- Correção do apontamento de lint pré-existente em `useActiveWorkspace`.
