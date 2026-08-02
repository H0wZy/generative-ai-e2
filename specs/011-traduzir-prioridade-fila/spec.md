# Feature Specification: Tradução da prioridade exibida na fila e no detalhe de ticket

**Feature Branch**: `011-traduzir-prioridade-fila`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "vc n corrigiu a tradução do painel: em prioridade está high, low etc, deixe em pt br."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prioridade em português na fila de tickets (Priority: P1)

Como analista consultando a fila de tickets ITSM, quero ver a prioridade de
cada ticket em português (Urgente, Alta, Média, Baixa), para não encontrar
o valor bruto em inglês (urgent, high, medium, low) misturado ao resto da
tela, que já está em português.

**Why this priority**: é um valor visível em toda linha da tabela — o
filtro de prioridade já mostra as opções traduzidas (Urgente, Alta, Média,
Baixa), mas o selo (badge) de prioridade em cada linha da tabela mostra o
valor cru vindo da origem, criando uma inconsistência óbvia dentro da
mesma tela.

**Independent Test**: abrir a fila de tickets com tickets de diferentes
prioridades e verificar que o selo de prioridade de cada linha mostra o
rótulo em português, nunca o valor em inglês.

**Acceptance Scenarios**:

1. **Given** a fila de tickets tem um ticket com prioridade "urgent",
   **When** a tabela é renderizada, **Then** o selo mostra "Urgente".
2. **Given** a fila de tickets tem tickets com prioridade "high", "medium"
   e "low", **When** a tabela é renderizada, **Then** os selos mostram
   "Alta", "Média" e "Baixa" respectivamente.
3. **Given** um ticket chega com um valor de prioridade fora do conjunto
   conhecido (urgent/high/medium/low), **When** a tabela é renderizada,
   **Then** o selo mostra o valor original em vez de quebrar ou mostrar
   texto vazio.

---

### User Story 2 - Prioridade em português no detalhe do ticket (Priority: P2)

Como analista abrindo o detalhe de um ticket específico, quero ver o mesmo
rótulo de prioridade em português que já vejo na fila, para ter uma
experiência consistente entre a lista e o detalhe.

**Why this priority**: mesmo problema, tela diferente — a tela de detalhe
também exibe o valor bruto (`detail.ticket.priority`) sem tradução; menor
prioridade que a fila porque é acessada com menos frequência.

**Independent Test**: abrir o detalhe de um ticket com prioridade "high" e
confirmar que o campo "Prioridade" mostra "Alta", não "high".

**Acceptance Scenarios**:

1. **Given** o usuário abre o detalhe de um ticket com prioridade "urgent",
   **When** a tela carrega, **Then** o campo "Prioridade" mostra "Urgente".
2. **Given** o mesmo ticket tem o formulário de edição pré-preenchido,
   **When** o formulário é aberto, **Then** o valor interno de prioridade
   usado para submissão continua sendo o valor original em inglês (o
   contrato com a API não muda) — apenas a exibição ao usuário é traduzida.

---

### Edge Cases

- Prioridade ausente/nula no ticket: selo/campo mostra um estado neutro
  (ex. "—"), não a string "null" nem quebra a renderização.
- Prioridade com valor desconhecido (não é urgent/high/medium/low): sistema
  exibe o valor original em vez de ocultar a informação ou lançar erro —
  mesmo comportamento hoje aplicado a squads desconhecidas.
- Comparação de valor de prioridade para lógica de negócio (ex. ordenação,
  filtro) continua usando o valor original em inglês vindo da origem — só a
  exibição ao usuário é traduzida, não o dado armazenado nem o contrato de
  filtro por querystring.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O selo de prioridade em cada linha da fila de tickets DEVE
  exibir o rótulo em português correspondente ao valor de prioridade
  (urgent → Urgente, high → Alta, medium → Média, low → Baixa).
- **FR-002**: O campo de prioridade na tela de detalhe do ticket DEVE
  exibir o mesmo rótulo em português usado na fila, para o mesmo valor de
  prioridade.
- **FR-003**: A tabela de tradução de prioridade usada no selo/detalhe
  DEVE ser a mesma (ou equivalente) à já usada no filtro de prioridade da
  fila, para não haver duas fontes de rótulo divergentes.
- **FR-004**: Um valor de prioridade fora do conjunto conhecido DEVE
  continuar sendo exibido (o valor original), nunca ocultado ou substituído
  por um erro visual.
- **FR-005**: A tradução de exibição NÃO PODE alterar o valor de
  prioridade usado em filtros, ordenação, submissão de formulário ou
  qualquer chamada à API — a tradução é só de apresentação.

### Key Entities

- **Prioridade do ticket**: valor de domínio vindo da origem (Freshservice),
  hoje em inglês (urgent, high, medium, low), exibido em português na
  interface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos selos de prioridade exibidos na fila de tickets
  mostram um rótulo em português para os quatro valores conhecidos.
- **SC-002**: O campo de prioridade da tela de detalhe do ticket mostra o
  mesmo rótulo em português usado na fila, para os mesmos valores.
- **SC-003**: Nenhuma chamada de filtro, ordenação ou submissão de
  formulário muda de comportamento após a tradução (verificável pela
  suíte de testes existente continuando a passar).

## Assumptions

- O conjunto de valores possíveis de prioridade é o já mapeado no filtro
  existente (`urgent`, `high`, `medium`, `low`) — não há evidência de
  outros valores na origem hoje.
- Esta spec cobre apenas a exibição de prioridade; o selo de status já é
  traduzido corretamente hoje e não faz parte do escopo.
