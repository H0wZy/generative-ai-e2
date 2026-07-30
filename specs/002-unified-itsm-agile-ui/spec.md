# Feature Specification: Plataforma Unificada ITSM + Agile

**Feature Branch**: `002-unified-itsm-agile-ui`

**Created**: 2026-07-28

**Status**: Draft

**Input**: Refatorar o frontend para ser user-friendly, com UI/UX coerente, unindo o que já funciona (fila de execuções Freshservice→Jira e painel analítico) ao protótipo aprovado "ITSM Agile Platform" — um workspace único que junta ITSM (Freshservice) e Agile (Jira) para apresentar o projeto.

## Contexto e Problema

O frontend atual são duas telas desconexas: uma tabela de execuções de workflow e um painel analítico com upload de planilha. Não há navegação, hierarquia visual, identidade ou noção de produto. Um avaliador que abre a aplicação não entende que existe uma tese por trás — a de que operação de suporte (ITSM) e entrega de engenharia (Agile) são o mesmo fluxo de trabalho, hoje partido entre duas ferramentas.

Existe um protótipo de alta fidelidade aprovado que resolve isso: um shell único com troca de workspace ITSM ↔ Agile, KPIs cruzados na home, e um assistente de IA transversal aos dois lados. Esta feature adota esse protótipo como destino e liga cada tela a dados reais.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Shell unificado e Home executiva (Priority: P1)

Um avaliador ou gestor abre a plataforma e cai numa Home que responde, numa tela, "como está a operação hoje?" — incidentes abertos, cumprimento de SLA, itens críticos, progresso do sprint corrente e carga por pessoa. A partir daí ele alterna entre o workspace **ITSM** e o workspace **Agile** por um controle único, e cada workspace troca a navegação lateral para o seu próprio conjunto de seções. O tema claro/escuro é alternável e persiste entre visitas.

**Why this priority**: É a mudança que cria a impressão de produto. Sem o shell, todo o resto continua parecendo telas soltas. É também a única história que entrega valor mesmo se nenhuma das outras for concluída, porque a Home consome métricas que já existem.

**Independent Test**: Abrir a raiz da aplicação, confirmar KPIs preenchidos com números vindos da operação real, alternar workspace e ver a navegação lateral mudar, alternar tema e recarregar a página confirmando que a escolha foi mantida.

**Acceptance Scenarios**:

1. **Given** a aplicação carregada pela primeira vez, **When** o usuário chega na Home, **Then** vê blocos de KPI de ITSM e de Agile lado a lado, cada um com valor numérico, rótulo e indicação da janela de tempo considerada.
2. **Given** o usuário no workspace ITSM, **When** aciona o seletor de workspace para Agile, **Then** a navegação lateral passa a listar as seções de Agile e a seção ativa é o Dashboard de Agile, sem recarregar a página inteira.
3. **Given** o tema escuro ativo, **When** o usuário alterna para claro e recarrega, **Then** a aplicação abre em tema claro.
4. **Given** uma origem de dados indisponível, **When** a Home carrega, **Then** os KPIs afetados exibem estado de indisponibilidade identificável (não zero, não vazio silencioso) e os demais KPIs continuam renderizando.
5. **Given** um teclado apenas, **When** o usuário navega pela sidebar e pelo seletor de workspace, **Then** todos os controles são alcançáveis por Tab, têm foco visível e são acionáveis por Enter/Espaço.

---

### User Story 2 - Operação ITSM: fila e detalhe de ticket (Priority: P1)

Um operador precisa ver a fila de tickets/execuções, entender rapidamente o que está fora do padrão (falha, retry, revisão humana, SLA em risco), abrir um item para ver o histórico completo do que aconteceu — incluindo as decisões automáticas de roteamento e o resultado da criação no Jira — e disparar reprocessamento quando aplicável.

**Why this priority**: É a funcionalidade que já existe e é a razão de ser do backend. Redesenhá-la e adicionar o detalhe transforma uma tabela num fluxo de trabalho.

**Independent Test**: Listar tickets, filtrar por status e prioridade, abrir um item em falha, ler a timeline, acionar reprocessar e ver o status do item mudar sem sair da tela.

**Acceptance Scenarios**:

1. **Given** a lista de tickets, **When** ela carrega, **Then** cada linha mostra identificador, assunto, prioridade, status, responsável e situação de SLA, com destaque visual para itens em falha, retry ou revisão humana.
2. **Given** a lista carregada, **When** o usuário filtra por status, prioridade ou squad e busca por texto, **Then** a lista reflete os critérios combinados e o número de resultados é exibido.
3. **Given** um ticket na lista, **When** o usuário o seleciona, **Then** abre o detalhe com assunto, solicitante, categoria, impacto, urgência, SLA, timeline cronológica de eventos e a issue Jira vinculada quando existir.
4. **Given** um ticket em falha ou aguardando revisão humana, **When** o usuário aciona reprocessar, **Then** recebe confirmação da ação e o status do item é atualizado na tela sem recarga manual.
5. **Given** um ticket que não é elegível a reprocessamento, **When** o detalhe é exibido, **Then** a ação de reprocessar não está disponível e o motivo é comunicado.
6. **Given** a lista com muitos itens, **When** o usuário rola até o fim, **Then** consegue avançar para o próximo conjunto de resultados sem perder os filtros aplicados.

---

### User Story 3 - Workspace Agile alimentado pelo Jira (Priority: P2)

Um líder técnico alterna para o workspace Agile e vê o sprint corrente com meta, progresso de pontos, dias restantes, curva de burndown, itens bloqueados e velocidade histórica. Navega para o Backlog ordenado por rank e agrupado por épico, e para os quadros Scrum e Kanban, onde pode mover um card entre colunas.

**Why this priority**: É o que sustenta a tese de plataforma unificada. Depende de leitura no Jira, que hoje só é usado para escrita, então tem custo e risco maiores que P1.

**Independent Test**: Com credenciais de Jira configuradas, abrir o Dashboard de Agile e confirmar que sprint, pontos e itens correspondem ao board real; abrir o quadro Scrum e mover um card de coluna.

**Acceptance Scenarios**:

1. **Given** um board Jira configurado com sprint ativo, **When** o Dashboard de Agile carrega, **Then** exibe nome e objetivo do sprint, datas de início e fim, dias restantes, pontos comprometidos e concluídos, e a curva de burndown ideal contra a real.
2. **Given** itens sem progresso ou marcados como impedidos, **When** o dashboard carrega, **Then** eles aparecem numa lista de bloqueios com título, motivo, responsável e há quantos dias estão parados.
3. **Given** o Backlog, **When** carrega, **Then** os itens vêm na ordem de rank do Jira, com épico, prioridade e estimativa, e um resumo de progresso por épico.
4. **Given** o quadro Scrum ou Kanban, **When** carrega, **Then** as colunas correspondem às colunas do board no Jira e cada card mostra chave, título, estimativa, etiquetas e responsável.
5. **Given** uma coluna Kanban com limite de trabalho em progresso definido, **When** a contagem de cards excede o limite, **Then** a coluna sinaliza o estouro visualmente.
6. **Given** um card em um quadro, **When** o usuário o arrasta para outra coluna, **Then** o card muda de coluna e a transição correspondente é aplicada no Jira; se o Jira recusar a transição, o card retorna à coluna de origem e a recusa é comunicada nomeando as transições disponíveis a partir do status atual.
7. **Given** credenciais de Jira ausentes ou inválidas, **When** qualquer tela de Agile carrega, **Then** exibe um estado de indisponibilidade que nomeia a causa e orienta a configuração, sem quebrar o resto da aplicação.
8. **Given** um board sem sprint ativo, **When** o Dashboard de Agile carrega, **Then** exibe estado vazio explicando que não há sprint em andamento e oferece acesso ao Backlog.

---

### User Story 4 - Reports dentro do shell (Priority: P2)

O painel analítico existente — ingestão de planilha, filtros por dimensão, throughput, distribuição de trabalho, lead time e cobertura de vínculo entre chamado e card — passa a ser a seção **Reports**, acessível a partir de ambos os workspaces, dentro da mesma navegação e da mesma linguagem visual.

**Why this priority**: Reaproveita funcionalidade pronta e preenche uma seção que o protótipo previa apenas como placeholder. Sem isso, a análise continua sendo uma aplicação paralela.

**Independent Test**: A partir da sidebar de qualquer workspace, abrir Reports, aplicar filtros e confirmar que os gráficos respondem; com base vazia, confirmar que a tela de ingestão é oferecida.

**Acceptance Scenarios**:

1. **Given** o usuário em qualquer workspace, **When** aciona Reports na navegação, **Then** a seção abre dentro do shell, preservando sidebar, tema e seletor de workspace.
2. **Given** nenhuma base carregada, **When** Reports abre, **Then** apresenta o fluxo de ingestão de arquivo em vez de gráficos vazios.
3. **Given** base carregada, **When** o usuário ajusta filtros e periodicidade, **Then** throughput, distribuição, lead time e cobertura são recalculados e a seleção ativa fica visível.
4. **Given** um recorte de filtros sem resultados, **When** aplicado, **Then** cada visualização exibe estado vazio explícito em vez de gráfico em branco.

---

### User Story 5 - Assistente de IA com respostas fundamentadas (Priority: P3)

Qualquer usuário abre o Assistente e faz uma pergunta em linguagem natural sobre a operação ou sobre a arquitetura do projeto — "o sprint 24 está em risco?", "por que o chamado X falhou?", "como funciona a idempotência do worker?". O assistente responde em texto corrido, sempre acompanhado das fontes que embasaram a resposta, e o usuário pode abrir cada fonte.

**Why this priority**: É o diferencial de Gen AI do projeto e o que mais impressiona numa apresentação, mas depende das outras histórias para ter dados sobre os quais responder.

**Independent Test**: Enviar uma pergunta sobre a arquitetura do projeto e verificar que a resposta cita trechos recuperados da base de conhecimento, com identificação de origem; enviar uma pergunta sem correspondência na base e verificar que o assistente declara não ter fundamento em vez de inventar.

**Acceptance Scenarios**:

1. **Given** o Assistente aberto, **When** o usuário envia uma pergunta, **Then** vê indicação de processamento e, ao final, uma resposta acompanhada da lista de fontes consultadas.
2. **Given** uma resposta exibida, **When** o usuário aciona uma fonte, **Then** vê o trecho recuperado e sua origem.
3. **Given** uma pergunta sem correspondência relevante na base de conhecimento, **When** processada, **Then** o assistente declara explicitamente que não encontrou fundamento e não produz uma resposta afirmativa.
4. **Given** o provedor de modelo indisponível, com erro ou fora do limite de uso, **When** o usuário envia uma pergunta, **Then** recebe mensagem que distingue indisponibilidade de ausência de resposta, e os trechos recuperados são exibidos mesmo sem a redação final.
5. **Given** o histórico da conversa na sessão, **When** o usuário envia uma pergunta de acompanhamento, **Then** ela é interpretada no contexto das mensagens anteriores da mesma sessão.
6. **Given** dados de ticket contendo informação pessoal identificável, **When** compõem o contexto enviado ao provedor de modelo, **Then** os campos pessoais são removidos ou mascarados antes do envio.

---

### Edge Cases

- Backend fora do ar na carga inicial: cada seção exibe erro próprio e o shell permanece navegável.
- Jira responde lento ou com throttling: telas de Agile mostram estado de carregamento limitado no tempo e, ao expirar, oferecem nova tentativa.
- Sprint com escopo alterado no meio do caminho: o burndown reflete o escopo adicionado sem distorcer a linha ideal.
- Card sem estimativa em pontos ou sem responsável: renderiza com o campo ausente marcado, não quebra a coluna.
- Board Jira com colunas que não mapeiam para o modelo Scrum/Kanban esperado: as colunas reais do board são usadas, sem forçar um conjunto fixo.
- Arraste de card interrompido fora de uma coluna válida: nenhuma alteração é aplicada.
- Ticket sem issue Jira vinculada: o detalhe mostra ausência de vínculo, não um link quebrado.
- Reprocessamento acionado duas vezes em sequência rápida: apenas uma solicitação é efetivada.
- Sessão de chat muito longa: o contexto enviado ao modelo é truncado por regra conhecida, e o usuário é informado quando isso ocorre.
- Resposta do modelo excede o tempo aceitável: a solicitação é interrompida e comunicada como tal.
- Viewport estreito: as tabelas e quadros rolam horizontalmente dentro do próprio contêiner, sem gerar rolagem horizontal na página.
- Usuário com preferência de movimento reduzido: transições e animações são suprimidas.

## Requirements *(mandatory)*

### Shell, navegação e identidade visual

- **FR-001**: A aplicação MUST apresentar um shell persistente composto por navegação lateral, barra superior com contexto da seção atual, e área de conteúdo.
- **FR-002**: A aplicação MUST oferecer um seletor de workspace com dois estados, ITSM e Agile, que altera o conjunto de seções da navegação lateral e a seção padrão exibida.
- **FR-003**: A navegação lateral MUST expor, no workspace ITSM: Home, Dashboard, Assets, Base de Conhecimento, Reports, Automações, Assistente de IA e Administração; e no workspace Agile: Home, Dashboard, Backlog, Quadro Scrum, Quadro Kanban, Reports, Assistente de IA e Administração.
- **FR-004**: Seções ainda não implementadas MUST renderizar um estado "em construção" nomeado, em vez de link inerte ou erro.
- **FR-005**: A aplicação MUST suportar tema claro e escuro, com alternância explícita, respeito à preferência do sistema na primeira visita e persistência da escolha do usuário.
- **FR-006**: Toda a interface MUST usar um conjunto único e declarado de tokens de cor, tipografia, espaçamento, raio e elevação, derivado do protótipo aprovado; nenhuma tela pode introduzir valores visuais avulsos.
- **FR-007**: Todo estado de carregamento, vazio e erro MUST ser explícito e distinguível dos demais em cada seção.
- **FR-008**: A interface MUST ser navegável por teclado com foco visível, ter alvos de toque adequados, respeitar preferência de movimento reduzido e atingir contraste mínimo de 4.5:1 para texto e 3:1 para elementos gráficos de interface, em ambos os temas.
- **FR-009**: A interface MUST ser utilizável em viewport a partir de 360 px de largura, com tabelas e quadros rolando dentro do próprio contêiner.

### Home

- **FR-010**: A Home MUST exibir indicadores de ITSM — incidentes abertos, cumprimento de SLA, itens críticos e volume ao longo do tempo — e de Agile — progresso do sprint e dias restantes — na mesma tela.
- **FR-011**: A Home MUST exibir a distribuição de carga de trabalho por responsável e a velocidade histórica das últimas iterações.
- **FR-012**: Cada indicador MUST declarar a janela de tempo a que se refere.
- **FR-013**: Indicadores cuja origem de dados esteja indisponível MUST ser marcados como indisponíveis, sem impedir a renderização dos demais.

### ITSM

- **FR-014**: A seção MUST listar tickets com identificador, assunto, prioridade, status, responsável, situação de SLA e destaque visual para exceções.
- **FR-015**: Usuários MUST poder filtrar a lista por status, prioridade e squad, e buscar por texto no assunto ou identificador, com os critérios combináveis e o total de resultados visível.
- **FR-016**: A lista MUST permitir avançar por conjuntos de resultados preservando filtros.
- **FR-017**: Usuários MUST poder abrir o detalhe de um ticket, contendo solicitante, categoria, impacto, urgência, SLA, decisão de roteamento com seu grau de confiança, e a issue Jira vinculada quando houver.
- **FR-018**: O detalhe MUST exibir uma timeline cronológica dos eventos da execução, incluindo tentativas, falhas e o motivo de cada uma.
- **FR-019**: Usuários MUST poder acionar reprocessamento em tickets elegíveis, com confirmação do resultado e atualização do estado na tela.
- **FR-020**: Acionamentos repetidos de reprocessamento sobre o mesmo ticket em curto intervalo MUST resultar em uma única solicitação efetiva.
- **FR-021**: O detalhe MUST oferecer navegação de volta à lista preservando o estado de filtros anterior.

### Agile

- **FR-022**: O sistema MUST ler, de um board configurado no Jira, o sprint ativo com nome, objetivo, datas, pontos comprometidos e pontos concluídos.
- **FR-023**: O Dashboard de Agile MUST exibir a curva de burndown do sprint corrente comparando a linha ideal com a real, refletindo escopo adicionado durante o sprint.
- **FR-024**: O Dashboard de Agile MUST listar itens impedidos ou parados com título, motivo, responsável e tempo de parada.
- **FR-025**: O Dashboard de Agile MUST exibir a velocidade das iterações anteriores.
- **FR-026**: O Backlog MUST listar itens na ordem de rank do Jira, com épico, prioridade e estimativa, e resumo de progresso por épico.
- **FR-027**: Os quadros Scrum e Kanban MUST derivar suas colunas das colunas reais do board no Jira, e exibir em cada card chave, título, estimativa, etiquetas e responsável.
- **FR-028**: O quadro Kanban MUST sinalizar visualmente colunas cuja contagem de cards excede o limite de trabalho em progresso definido no board.
- **FR-029**: Usuários MUST poder mover um card entre colunas por arraste, aplicando a transição correspondente no Jira; falha na transição MUST reverter a posição do card e comunicar o motivo.
- **FR-030**: Toda seção de Agile MUST degradar para um estado de indisponibilidade nomeado quando as credenciais de Jira estiverem ausentes ou a integração falhar, sem afetar as demais seções.
- **FR-031**: Os dados de Agile MUST ser servidos pela API do projeto, e não obtidos pelo navegador diretamente do Jira, de modo que credenciais nunca cheguem ao cliente.

### Reports

- **FR-032**: A seção Reports MUST estar acessível a partir de ambos os workspaces e renderizar dentro do shell.
- **FR-033**: Reports MUST preservar as capacidades atuais de ingestão de arquivo, filtros por dimensão, seleção de periodicidade, throughput, distribuição de trabalho, lead time e cobertura de vínculo.
- **FR-034**: Com base de dados vazia, Reports MUST oferecer o fluxo de ingestão em vez de visualizações vazias.
- **FR-035**: Recortes de filtro sem resultados MUST produzir estado vazio explícito em cada visualização.

### Assistente de IA

- **FR-036**: Usuários MUST poder enviar perguntas em linguagem natural e receber resposta em texto, acompanhada das fontes recuperadas da base de conhecimento.
- **FR-037**: Cada fonte MUST ser inspecionável, exibindo o trecho recuperado e sua origem.
- **FR-038**: Quando a recuperação não retornar material relevante, o assistente MUST responder com seu conhecimento geral dentro do escopo do projeto, indicando de forma clara que a resposta não é fundamentada na documentação indexada.
- **FR-038a**: Perguntas sem relação com o escopo do projeto (a automação ITSM/Freshservice, o workspace Agile/Jira, o pipeline RAG e a arquitetura deste sistema) MUST ser recusadas educadamente em vez de respondidas.
- **FR-039**: O assistente MUST manter o contexto das mensagens anteriores dentro da mesma sessão.
- **FR-040**: O contexto enviado ao provedor de modelo MUST ter campos de informação pessoal identificável removidos ou mascarados.
- **FR-041**: O provedor e o modelo de linguagem MUST ser configuráveis por ambiente, sem alteração de código.
- **FR-042**: Credenciais do provedor de modelo MUST permanecer no servidor, nunca expostas ao navegador nem registradas em log.
- **FR-043**: Falha, indisponibilidade, estouro de limite de uso ou tempo excedido do provedor MUST ser comunicados de forma distinguível entre si, e os trechos recuperados MUST ser exibidos ainda que a redação final não seja produzida.
- **FR-044**: O sistema MUST impor um teto de tempo por pergunta e um teto de tamanho de contexto, informando o usuário quando o histórico for truncado.
- **FR-045**: Conteúdo recuperado da base de conhecimento e conteúdo de tickets MUST ser tratado como dado, não como instrução ao modelo.

- **FR-046**: O movimento de card entre colunas MUST resultar em escrita real no Jira: a transição de status correspondente é aplicada à issue e o estado exibido passa a refletir o estado retornado pelo Jira, não o estado otimista da interface.
- **FR-047**: Quando o Jira não oferecer transição direta entre o status de origem e o de destino, o sistema MUST comunicar a recusa nomeando as transições que estão disponíveis a partir do status atual, em vez de uma falha genérica.
- **FR-048**: A interface MUST refletir o movimento imediatamente e reverter o card à coluna de origem caso a escrita no Jira falhe, sem exigir recarga da tela.

### Key Entities

- **Workspace**: Contexto de trabalho ativo, ITSM ou Agile; determina o conjunto de seções navegáveis e a seção padrão.
- **Ticket**: Item de suporte originado no Freshservice, com identificador de origem, assunto, categoria, impacto, urgência, solicitante, prioridade, status, situação de SLA e vínculo opcional com uma issue do Jira.
- **Execução de workflow**: Processamento de um ticket, com status, número de tentativas, decisão de roteamento e grau de confiança, e resultado da criação no Jira. É a entidade que a fila do ITSM lista e que o reprocessamento retoma.
- **Evento de timeline**: Ocorrência datada no ciclo de vida de uma execução — recebimento, roteamento, tentativa, falha com motivo, criação de issue, reprocessamento.
- **Sprint**: Iteração do board Jira, com nome, objetivo, datas, pontos comprometidos, concluídos e adicionados em escopo.
- **Item de trabalho**: Issue do Jira, com chave, título, épico, estimativa, etiquetas, responsável, prioridade, coluna atual e posição de rank.
- **Épico**: Agrupador de itens de trabalho, com nome, cor e progresso agregado.
- **Coluna de board**: Coluna do board Jira, com nome, mapeamento de status e limite opcional de trabalho em progresso.
- **Indicador**: Métrica exibida na Home ou nos dashboards, com valor, rótulo, janela de tempo e estado de disponibilidade.
- **Mensagem do assistente**: Turno de conversa, com autor, texto, momento e — quando resposta — o conjunto de fontes recuperadas.
- **Fonte recuperada**: Trecho de conhecimento com texto, origem identificável e grau de relevância.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Um avaliador que nunca viu a plataforma consegue, em até 60 segundos a partir da Home e sem orientação, identificar quantos incidentes estão abertos e qual o progresso do sprint corrente.
- **SC-002**: Um operador consegue localizar um ticket em falha, abrir seu detalhe, entender o motivo da falha e disparar reprocessamento em até 4 interações a partir da Home.
- **SC-003**: Alternar entre workspaces ITSM e Agile leva menos de 1 segundo percebido e não exige recarregar a página.
- **SC-004**: Toda seção implementada apresenta estados distintos e reconhecíveis para carregando, vazio e erro — verificável em 100% das seções.
- **SC-005**: A interface passa em verificação automatizada de acessibilidade sem violações de nível A ou AA em ambos os temas, em todas as seções implementadas.
- **SC-006**: Nenhuma página produz rolagem horizontal em viewport de 360 px de largura.
- **SC-007**: A Home apresenta conteúdo utilizável em até 2 segundos em conexão de banda larga típica.
- **SC-008**: Indisponibilidade de qualquer integração externa não impede o uso das seções que não dependem dela — verificável desligando cada integração isoladamente.
- **SC-009**: 100% das respostas do assistente exibem as fontes que as embasaram, ou declaram explicitamente ausência de fundamento.
- **SC-010**: Nenhuma credencial de Jira ou de provedor de modelo aparece em resposta enviada ao navegador ou em log da aplicação — verificável por inspeção do tráfego e dos logs.
- **SC-011**: Nenhum valor visual fora do conjunto declarado de tokens é usado nas telas implementadas.
- **SC-012**: Um usuário consegue chegar a qualquer seção implementada com no máximo dois acionamentos a partir da Home.
- **SC-013**: Um card movido entre colunas reflete o novo status no Jira em até 3 segundos, ou reverte à posição de origem com motivo nomeado — verificável comparando o quadro com o Jira após o movimento.

## Assumptions

- A plataforma continua sem autenticação de usuário no escopo desta feature; identidade e permissão ficam para um trabalho posterior. Avatares e nomes de responsável vêm dos dados de origem, não de sessão autenticada.
- O board e o projeto do Jira usados pelo workspace Agile são configuração de ambiente, um por instalação; seleção de múltiplos boards pela interface está fora do escopo.
- As seções Assets, Base de Conhecimento, Automações e Administração permanecem como estados "em construção" nesta feature — estão na navegação para completar a narrativa do produto, sem funcionalidade.
- O provedor de modelo de linguagem é acessado por uma interface compatível com o padrão de mercado, permitindo trocar provedor e modelo por configuração. O modelo padrão adotado é `nvidia/nemotron-3-ultra-550b-a55b:free`, servido via OpenRouter; a escolha é configuração de ambiente e não deve ser assumida por nenhuma tela.
- O plano gratuito impõe limites de requisição e latência maiores que um plano pago, o que motiva os requisitos de tempo máximo por pergunta, teto de contexto e comunicação distinguível de estouro de limite. Um modelo desta escala em tier gratuito pode responder na casa das dezenas de segundos sob carga — o teto de tempo precisa ser generoso o suficiente para não cortar respostas válidas e curto o suficiente para não travar a demo.
- Modelos gratuitos podem reter prompts para treinamento do provedor; por isso a remoção de informação pessoal antes do envio é requisito, não recomendação.
- Se o modelo padrão estiver indisponível ou fora do limite, o comportamento esperado é a comunicação prevista em FR-043, não a troca automática para outro modelo.
- A base de conhecimento do assistente é a documentação e arquitetura do projeto já indexada, exposta à API por um serviço interno.
- O conteúdo da interface permanece em português brasileiro; internacionalização está fora do escopo.
- A linguagem visual e a estrutura de telas seguem o protótipo aprovado "ITSM Agile Platform"; divergências em relação a ele são decisões conscientes e devem ser registradas.
- A ingestão de dados do painel analítico permanece por upload de arquivo, como hoje; sincronização automática está fora do escopo.

## Dependencies

- API do projeto para métricas, fila de execuções, detalhe e reprocessamento — já existente.
- API do projeto para o painel analítico, incluindo ingestão e agregações — já existente.
- Leitura no Jira de boards, sprints, issues e transições — **não existente hoje**; a integração atual apenas cria issues.
- Serviço de busca na base de conhecimento do projeto — existe como servidor MCP, **sem interface HTTP**; precisa ser exposto à API.
- Provedor de modelo de linguagem com chave de acesso configurada no ambiente do servidor.

## Out of Scope

- Autenticação, autorização e perfis de usuário.
- Criação e edição de tickets ou de issues pela interface. A única escrita prevista é a transição de status por movimento de card (FR-046) e o reprocessamento de execução (FR-019).
- Notificações, tempo real e push.
- Aplicativo móvel nativo.
- Seleção de múltiplos projetos ou boards pela interface.
- Internacionalização.
