# Feature Specification: Refresh Operacional — Ticket ao Vivo, Assistente Persistente, Identidade Visual

**Feature Branch**: `003-unified-ops-refresh`

**Created**: 2026-07-30

**Status**: Draft

**Input**: User description: "Refatoração ampla da plataforma unificada ITSM+Agile (specs/002): CRUD de ticket ITSM integrado ao Jira real, unificação do provedor de LLM no OpenRouter, persistência de conversas do assistente, assistente consultando dados de ticket sob demanda, formatação de saída do assistente (markdown + links de navegação), remoção da seção Reports, correção do bug de navegação da sidebar, e identidade visual nova (paleta near-black + acento brass, tipografia Archivo/IBM Plex, trilho de status)."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Criar e acompanhar um chamado que vira issue real no Jira (Priority: P1)

Uma pessoa abre um chamado na tela de ITSM da plataforma (sem precisar do Freshservice real, que não está disponível para demonstração). O chamado é registrado, roteado para a squad certa, e uma issue real aparece no board do Jira em segundos — não em um próximo ciclo de sincronização. A pessoa acompanha o chamado na mesma tela, edita informações enquanto ele está aberto, e marca como concluído quando resolvido.

**Why this priority**: É a narrativa central da demonstração — provar que ITSM e Agile são a mesma plataforma, não dois sistemas emendados. Sem isso, não há histórico de demo para gravar.

**Independent Test**: Abrir um chamado pela tela, sem tocar em nada mais, e conferir que uma issue nova aparece no Jira real com a squad e prioridade corretas, e que a tela mostra o link para ela.

**Acceptance Scenarios**:

1. **Given** a tela de novo chamado, **When** a pessoa preenche assunto, descrição e prioridade e confirma, **Then** o chamado aparece imediatamente na lista com status "processando" e, em poucos segundos, com a chave da issue criada no Jira.
2. **Given** um chamado já criado e ainda aberto, **When** a pessoa edita o assunto ou a descrição, **Then** a mudança é salva e refletida na próxima vez que a tela é aberta.
3. **Given** um chamado resolvido na prática, **When** a pessoa marca como concluído, **Then** o status muda e fica visível na lista sem precisar recarregar a página.
4. **Given** falha ao criar a issue no Jira (credencial recusada, Jira fora do ar), **When** o chamado é criado, **Then** a tela mostra um estado nomeado de falha (não um erro genérico) e o chamado continua visível para nova tentativa.

---

### User Story 2 - Identidade visual única e navegação sem ambiguidade (Priority: P2)

Toda a plataforma (ITSM, Agile, Assistente) usa a mesma paleta quase-neutra com um único acento de cor, a mesma tipografia, e o mesmo indicador visual de status em qualquer lista ou card. A barra lateral nunca troca de workspace sozinha ao clicar em uma seção que não pertence exclusivamente a um dos dois lados.

**Why this priority**: É a segunda coisa mais visível no vídeo de apresentação, logo depois do fluxo do chamado. Uma identidade inconsistente ou um bug de navegação visível prejudica a percepção de qualidade tanto quanto uma funcionalidade quebrada.

**Independent Test**: Navegar por todas as telas implementadas (Home, ITSM, Agile, Assistente) em sequência e confirmar visualmente paleta, tipografia e indicador de status idênticos; clicar em Reports (ou o que ficar no lugar) a partir do workspace Agile e confirmar que o workspace ativo não muda sozinho.

**Acceptance Scenarios**:

1. **Given** qualquer tela implementada, **When** a pessoa navega entre ITSM e Agile, **Then** a paleta de cor, a tipografia e o indicador de status (a barra lateral colorida em linhas e cards) são visualmente idênticos entre as duas.
2. **Given** a pessoa está no workspace Agile, **When** ela clica em um item de navegação que não é exclusivo de ITSM nem de Agile, **Then** o workspace ativo na barra lateral permanece Agile.
3. **Given** a seção Reports foi removida, **When** a pessoa navega pela barra lateral, **Then** não existe mais item de menu nem rota apontando para ela.

---

### User Story 3 - Conversa com o assistente sobrevive à navegação (Priority: P3)

Uma pessoa conversa com o assistente de IA, navega para outra tela ou fecha e reabre o navegador, e volta ao assistente encontrando o histórico da conversa intacto.

**Why this priority**: É uma quebra de expectativa básica de qualquer chat — perder a conversa ao trocar de aba é o tipo de detalhe que marca "protótipo", não "produto".

**Independent Test**: Fazer uma pergunta ao assistente, navegar para outra seção da plataforma, voltar ao assistente e confirmar que a pergunta e a resposta anteriores ainda aparecem.

**Acceptance Scenarios**:

1. **Given** uma conversa em andamento com o assistente, **When** a pessoa navega para outra tela e volta, **Then** todas as mensagens trocadas anteriormente na mesma visita ainda estão visíveis, na ordem em que ocorreram.
2. **Given** uma conversa em andamento, **When** a pessoa fecha o navegador e abre de novo no mesmo dispositivo, **Then** a conversa anterior ainda está disponível.
3. **Given** duas pessoas diferentes usando a plataforma em dispositivos diferentes, **When** cada uma conversa com o assistente, **Then** uma não vê a conversa da outra.

---

### User Story 4 - Assistente responde sobre um chamado específico e formata a resposta de forma legível (Priority: P4)

Uma pessoa pergunta ao assistente sobre um chamado específico (citando sua chave ou descrevendo a situação) e recebe uma resposta que usa negrito e links de verdade — não asteriscos crus — e, quando faz sentido, aponta para a tela exata da plataforma onde a informação pode ser conferida.

**Why this priority**: Completa a demonstração do assistente como parte funcional da plataforma (não só um Q&A sobre documentação), mas depende das User Stories 1 e 3 já existirem para ter chamado e conversa para consultar.

**Independent Test**: Perguntar ao assistente pelo status de um chamado existente citando sua chave, e perguntar "onde vejo o backlog" — conferir que a primeira resposta reflete o dado real do chamado e a segunda contém um link clicável para a tela de backlog.

**Acceptance Scenarios**:

1. **Given** um chamado existente com chave conhecida, **When** a pessoa pergunta ao assistente sobre o status desse chamado citando a chave, **Then** a resposta reflete o status real armazenado, sem inventar informação.
2. **Given** uma pergunta sem relação com nenhum chamado específico, **When** o assistente responde, **Then** nenhuma consulta a chamado é feita — mantém o comportamento já existente de busca em documentação.
3. **Given** uma resposta do assistente contém ênfase (negrito/itálico), **When** renderizada na tela, **Then** aparece como formatação visual real, nunca como asterisco ou sublinhado cru.
4. **Given** uma resposta do assistente menciona uma tela existente da plataforma, **When** renderizada, **Then** o nome da tela aparece como link clicável que navega até ela sem recarregar a página.

---

### Edge Cases

- O que acontece quando a pessoa cria um chamado e a issue correspondente falha ao ser criada no Jira (rede fora do ar, credencial recusada)? A pessoa vê um estado de falha nomeado e pode tentar de novo — o chamado não desaparece nem fica em limbo silencioso.
- O que acontece quando a pessoa pergunta ao assistente sobre uma chave de chamado que não existe? O assistente informa que não encontrou esse chamado, sem inventar um status.
- O que acontece quando duas pessoas marcam o mesmo chamado como concluído ao mesmo tempo? A segunda ação não gera erro nem duplica o registro — o estado final é "concluído" de qualquer forma.
- O que acontece quando a conversa do assistente cresce além do que cabe no contexto? Comportamento já existente (truncamento com aviso) é preservado.
- O que acontece com uma pergunta ao assistente completamente fora do escopo do projeto? Comportamento já existente (recusa educada) é preservado — esta feature não amplia nem restringe esse limite.

## Requirements *(mandatory)*

### Functional Requirements

**Chamado ao vivo (User Story 1)**

- **FR-049**: Usuários MUST poder criar um chamado preenchendo assunto, descrição, prioridade e categoria, sem depender de nenhum sistema externo de ticketing.
- **FR-050**: O sistema MUST roteá-lo para uma squad e criar uma issue correspondente em um sistema de rastreamento real, refletindo o resultado (sucesso ou falha nomeada) na mesma sessão em que o chamado foi criado — sem exigir espera por um ciclo de sincronização periódica.
- **FR-051**: Usuários MUST poder visualizar a lista de chamados criados, com status atual e link para a issue correspondente quando existir.
- **FR-052**: Usuários MUST poder editar assunto, descrição, prioridade e categoria de um chamado enquanto ele não estiver concluído.
- **FR-053**: Usuários MUST poder marcar um chamado como concluído; a ação MUST ser idempotente (repetir a ação não gera erro nem duplica o registro).
- **FR-054**: O sistema MUST NOT oferecer exclusão de chamado — uma vez criado, o histórico permanece (consistente com a issue já criada no sistema de rastreamento).

**Identidade e navegação (User Story 2)**

- **FR-055**: Toda tela da plataforma MUST usar a mesma paleta de cor, tipografia e indicador visual de status já aprovados, sem variação entre workspaces.
- **FR-056**: A navegação MUST preservar o workspace ativo (ITSM ou Agile) ao acessar uma seção compartilhada pelos dois, mudando de workspace apenas por ação explícita da pessoa.
- **FR-057**: A seção antiga de relatórios baseada em upload de arquivo histórico MUST ser removida da navegação e das rotas acessíveis.

**Assistente persistente (User Story 3)**

- **FR-058**: O sistema MUST manter o histórico de conversa do assistente entre navegações e entre sessões do navegador, sem exigir login.
- **FR-059**: O histórico de conversa MUST ser isolado por visitante — uma pessoa nunca vê a conversa de outra.

**Assistente com dado ao vivo e formatação (User Story 4)**

- **FR-060**: Quando uma pergunta ao assistente citar um chamado específico (por chave ou referência direta), o sistema MUST consultar o dado real desse chamado e usá-lo como contexto adicional, sem que isso seja obrigatório para nenhuma outra pergunta.
- **FR-061**: A consulta a dado de chamado MUST seguir a mesma regra já existente para busca de documentação: nunca é a única via de resposta, e sua ausência ou falha nunca bloqueia o assistente de responder.
- **FR-062**: Respostas do assistente MUST ser renderizadas com ênfase textual (negrito, itálico) interpretada visualmente, nunca como marcação crua.
- **FR-063**: Quando a resposta do assistente mencionar uma tela existente da plataforma, o sistema MUST oferecer um link de navegação interna clicável para ela.
- **FR-064**: Conteúdo recuperado de fonte não confiável (documentação indexada, ticket) permanece renderizado como texto simples (FR-045 do spec anterior não é alterado) — a formatação desta feature aplica-se somente ao texto gerado pelo próprio assistente.

### Requisitos supersedidos

- **FR-032 a FR-035** (specs/002, seção Reports) são removidos desta versão da plataforma — a seção Reports e seu fluxo de ingestão por upload deixam de existir, substituídos pelo dado ao vivo do chamado (User Story 1). Mantidos aqui apenas como registro histórico do que foi descontinuado e por quê.

### Key Entities

- **Chamado (Ticket)**: um pedido de suporte criado diretamente na plataforma — assunto, descrição, prioridade, categoria, squad, status, vínculo com a issue criada no sistema de rastreamento. É a mesma entidade de execução de workflow já existente (specs/002); esta feature adiciona a via de criação direta, não um novo tipo de dado.
- **Conversa do Assistente**: uma sequência de perguntas e respostas trocadas por um visitante, identificada por um id de sessão sem login, persistida entre visitas.
- **Vínculo Chamado↔Fonte**: quando o assistente usa dado de um chamado como contexto, esse vínculo é exposto ao usuário da mesma forma que uma fonte de documentação — identificável, não uma afirmação sem origem.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma pessoa cria um chamado e vê a issue correspondente aparecer no sistema de rastreamento real em menos de 15 segundos, sem recarregar a página manualmente.
- **SC-002**: 100% das telas implementadas usam a mesma paleta, tipografia e indicador de status — verificável por inspeção visual lado a lado.
- **SC-003**: Navegar entre as 8 seções da barra lateral não troca o workspace ativo em nenhum caso fora da navegação explícita entre ITSM e Agile.
- **SC-004**: Uma conversa com o assistente sobrevive a 100% das navegações de tela e a fechar/reabrir o navegador no mesmo dispositivo.
- **SC-005**: Uma pergunta citando a chave de um chamado existente reflete o status real armazenado em pelo menos 95% das tentativas em ambiente de teste controlado.
- **SC-006**: Nenhuma resposta do assistente exibida contém marcação de negrito/itálico/link crua (asterisco ou colchete literal) em uma amostra de 20 perguntas variadas.

## Assumptions

- O Freshservice real continua indisponível para a demonstração (ADR-011 do spec anterior); a criação direta de chamado pela própria plataforma é o substituto aceito, não uma segunda via permanente.
- "Sem login" para a sessão do assistente significa um identificador gerado no dispositivo da pessoa, não uma conta de usuário — consistente com o resto da plataforma, que não tem autenticação (limitação conhecida e documentada).
- A unificação do provedor de modelo (squad classifier e assistente no mesmo provedor pago) é uma mudança de infraestrutura interna sem impacto direto em nenhuma User Story desta spec; é tratada no plano técnico, não como requisito de produto aqui. Ela precisa de uma exceção de ADR à Constituição do projeto (modelos locais por padrão) — não é aprovação automática.
- O risco de bloqueio de rede corporativa (proxy) para o provedor de modelo, levantado durante o brainstorming, foi deliberadamente deixado fora do escopo desta feature por decisão do usuário; nenhuma User Story ou critério de sucesso aqui depende de resolvê-lo.
- Chamados criados diretamente pela plataforma reaproveitam o mesmo pipeline de roteamento e criação de issue já existente e avaliado (specs/002); esta feature não substitui esse pipeline, apenas adiciona uma via de entrada direta e torna o processamento imediato em vez de assíncrono por intervalo.
