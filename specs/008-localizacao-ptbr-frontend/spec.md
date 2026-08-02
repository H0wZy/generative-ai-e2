# Feature Specification: Localização PT-BR completa do frontend

**Feature Branch**: `008-localizacao-ptbr-frontend`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "Nova spec: localização PT-BR completa do frontend (dashboard ITSM/Ágil) — traduzir textos residuais em inglês (labels de navegação \"Home\"/\"Dashboard\"/\"Assets\", rótulo do workspace \"Agile\", botões de scroll \"Scroll to end\"/\"Scroll to start\" no assistente, e quaisquer outros textos de UI, KPIs e gráficos ainda em inglês) para português do Brasil, sem quebrar o mapeamento label→ícone em NAV_ICONS nem os testes/contratos existentes."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Navegação e workspace em português (Priority: P1)

Como usuário do dashboard (analista ITSM ou membro da squad ágil), quero que
todos os rótulos da barra lateral e do seletor de workspace apareçam em
português, para não encontrar termos em inglês misturados ao restante da
interface já traduzida.

**Why this priority**: é o texto mais visível da aplicação — aparece em toda
navegação, em todas as telas, o tempo todo. É também onde hoje existem os
casos confirmados de inglês solto ("Home", "Dashboard", "Assets" na sidebar;
"Agile" no seletor de workspace e na topbar).

**Independent Test**: abrir a sidebar em `/`, `/itsm` e `/agile` e conferir
que nenhum item de menu, título de seção ativa ou rótulo do seletor de
workspace mostra texto em inglês.

**Acceptance Scenarios**:

1. **Given** o usuário está em qualquer tela do shell, **When** a sidebar é
   renderizada, **Then** todos os `label` de `NAV` aparecem em português
   (ex.: "Home" → "Início", "Dashboard" → "Painel", "Assets" → "Ativos").
2. **Given** o usuário abre o seletor de workspace, **When** alterna entre
   ITSM e o workspace ágil, **Then** o rótulo mostrado é "Ágil", nunca
   "Agile".
3. **Given** o usuário está no workspace ágil, **When** olha a topbar,
   **Then** o rótulo da seção ativa também usa "Ágil".

---

### User Story 2 - Acessibilidade do Assistente em português (Priority: P2)

Como usuário de leitor de tela navegando pela conversa do Assistente de IA,
quero que os controles de rolagem (ir para o início/fim da conversa) sejam
anunciados em português, para ter a mesma experiência oferecida no resto do
produto.

**Why this priority**: afeta acessibilidade (texto `sr-only`), não é
cosmético — um usuário de leitor de tela ouve o texto em inglês hoje.

**Independent Test**: inspecionar o texto acessível dos botões de rolagem do
`message-scroller` na tela `/ai/chat/[id]` com uma árvore de acessibilidade
ou leitor de tela e confirmar que não há "Scroll to end"/"Scroll to start".

**Acceptance Scenarios**:

1. **Given** uma conversa longa aberta no Assistente, **When** o botão de
   rolagem para o fim da conversa recebe foco, **Then** o texto acessível
   está em português (ex.: "Ir para o fim da conversa").
2. **Given** a mesma tela, **When** o botão de rolagem para o início recebe
   foco, **Then** o texto acessível está em português (ex.: "Ir para o
   início da conversa").

---

### User Story 3 - Varredura completa de KPIs, gráficos e estados (Priority: P3)

Como responsável por revisar a interface antes de uma demonstração, quero uma
garantia de que nenhum card de KPI, gráfico, estado vazio/erro/indisponível
ou rótulo de formulário ficou para trás em inglês, para não ter surpresa em
produção.

**Why this priority**: cobre a cauda longa — texto que pode ter sido
esquecido fora dos pontos já mapeados nas Stories 1 e 2. Prioridade menor
porque a varredura já feita não encontrou ocorrências adicionais além das
listadas acima; esta story é a rede de segurança que confirma isso e evita
regressão.

**Independent Test**: rodar uma varredura de texto (grep) por literais em
inglês em `frontend/src/app` e `frontend/src/components`, revisando cada
resultado quanto a falso positivo (identificador técnico, nome de rota,
`data-slot`, valor de enum interno) versus texto exibido ao usuário.

**Acceptance Scenarios**:

1. **Given** a varredura de texto no código-fonte do frontend, **When** os
   resultados são filtrados para excluir identificadores técnicos
   (props, classes Tailwind, `data-slot`, chaves de enum), **Then** nenhuma
   string remanescente é texto de UI em inglês.
2. **Given** as telas de KPI (`/`, `/itsm`, `/agile`), **When** renderizadas
   com dado real ou mockado, **Then** todo rótulo de card, legenda de
   gráfico e estado vazio/erro/indisponível está em português.

---

### Edge Cases

- Rótulo de item de menu também é chave de busca em `NAV_ICONS`
  (`NAV_ICONS[item.label]`) — traduzir o `label` sem atualizar a chave
  correspondente quebra o ícone (cai no fallback `Home`). Toda tradução de
  `label` em `nav.ts` exige atualizar a chave em `NAV_ICONS` no mesmo commit.
- Enums vindos do backend (status, prioridade, causa de falha) já passam por
  tabela de tradução própria nos componentes ITSM/Ágil
  (`ticket-table.tsx`, `ticket-filters.tsx` etc.); esta spec não introduz
  tradução nova para eles, só garante que nenhum ainda cai no valor bruto em
  inglês por falta de entrada na tabela.
- Nomes de rota (`/agile`, `/itsm`, `/ai/chat`) e siglas de domínio (ITSM)
  são identificadores técnicos ou nomes próprios já usados nos handoffs — não
  são alvo de tradução.
- Textos vindos de bibliotecas de terceiros não sob controle do projeto
  (mensagens nativas do navegador, DevTools) ficam fora de escopo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A sidebar principal DEVE exibir todos os rótulos de navegação
  (`NAV` em `lib/nav.ts`) em português, incluindo os itens hoje em inglês
  ("Home", "Dashboard", "Assets").
- **FR-002**: O seletor de workspace (`workspace-switcher.tsx`) DEVE exibir
  "Ágil" para o workspace ágil, nunca "Agile".
- **FR-003**: A topbar (`topbar.tsx`) DEVE usar o mesmo rótulo em português
  do seletor de workspace para a seção ativa.
- **FR-004**: Os botões de rolagem do `message-scroller` usados no
  Assistente DEVEM ter texto acessível (`sr-only`) em português.
- **FR-005**: Nenhum outro texto estático voltado ao usuário — cards de KPI,
  título/legenda de gráfico, estado vazio, estado de erro, estado
  indisponível, rótulo de formulário e filtro — pode conter texto em inglês
  solto em `frontend/src/app` ou `frontend/src/components`.
- **FR-006**: A tradução de qualquer `label` usado como chave de
  `NAV_ICONS` DEVE manter o mapeamento label→ícone funcionando (a chave é
  atualizada junto, não deixada órfã).
- **FR-007**: A navegação ativa (`mostSpecificMatch`, `workspaceFor`,
  `sectionLabel`) DEVE continuar identificando corretamente a seção/rota
  atual depois da tradução dos rótulos, já que parte dessa lógica compara
  `href`, não `label`.
- **FR-008**: Testes e contratos existentes (specs 001–007, testes de
  frontend) que hoje afirmam ou fixam algum dos textos em inglês listados
  DEVEM ser atualizados no mesmo commit da tradução correspondente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos rótulos de navegação e do seletor de workspace
  renderizados nas telas `/`, `/itsm` e `/agile` estão em português.
- **SC-002**: Uma nova varredura de texto no frontend após a implementação
  não encontra nenhuma ocorrência de texto de UI em inglês (zero
  ocorrências, descontados identificadores técnicos e nomes próprios).
- **SC-003**: O texto acessível dos controles de rolagem do Assistente está
  em português, verificável por inspeção de acessibilidade.
- **SC-004**: A suíte de testes do frontend passa sem nenhuma falha
  atribuível a mudança de comportamento (só ajuste de texto esperado).
- **SC-005**: Nenhuma regressão de navegação — o item de menu correto
  continua destacado como ativo em cada rota, e o ícone correto continua
  aparecendo ao lado de cada rótulo traduzido.

## Assumptions

- Enums de domínio (status, prioridade, causa de falha) já têm tabela de
  tradução própria nos componentes ITSM/Ágil; esta spec cobre apenas texto
  estático de UI que hoje escapa em inglês cru, não a criação de um sistema
  de tradução de enum novo.
- "ITSM" permanece sigla técnica não traduzida, por já ser nome de domínio
  usado nos handoffs e na navegação.
- Escopo é `frontend/src` (App Router, componentes, libs de UI); não altera
  rotas (URLs seguem como identificador técnico em inglês), contratos de
  API ou nomes de campo do backend.
- Não é introduzida biblioteca de internacionalização (ex. `next-intl`) —
  troca direta das strings, mantendo o padrão atual do projeto (texto em
  português direto no componente, sem camada de i18n).
- A varredura de texto (Story 3) é uma tarefa de auditoria, não uma
  reescrita de arquitetura — se encontrar volume grande de ocorrências além
  do já mapeado, isso deve ser reportado antes de expandir o escopo desta
  spec.
