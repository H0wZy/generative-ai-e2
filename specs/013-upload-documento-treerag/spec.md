# Feature Specification: Upload de documento no chat com busca em árvore (TreeRAG)

**Feature Branch**: `013-upload-documento-treerag`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "Habilitar o botão de clipe (grampo) já existente e decorativo no compositor do chat do assistente para permitir que o usuário suba um arquivo/documento durante uma conversa, e o assistente use esse documento como fonte para responder perguntas concretas sobre ele, usando uma estratégia de recuperação em árvore (TreeRAG) com busca bidirecional (raiz→folha e folha→raiz), citação precisa de trecho/seção, e escopo efêmero por conversa (P1: texto/Markdown; P2: PDF com OCR)."

## User Scenarios & Testing *(mandatory)*

<!--
  IMPORTANT: User stories should be PRIORITIZED as user journeys ordered by importance.
  Each user story/journey must be INDEPENDENTLY TESTABLE - meaning if you implement just ONE of them,
  you should still have a viable MVP (Minimum Viable Product) that delivers value.
-->

### User Story 1 - Anexar texto/Markdown e obter resposta citada (Priority: P1)

Durante uma conversa com o assistente, a pessoa clica no clipe já visível no
compositor de mensagens, escolhe um arquivo de texto simples ou Markdown do
próprio computador, e o arquivo passa a valer como fonte para aquela conversa.
A partir daí, perguntas sobre o conteúdo do arquivo recebem respostas que
citam a seção e o trecho exato de onde a informação veio.

**Why this priority**: É o núcleo da feature. Sem isso não há upload
funcional nem resposta baseada em documento externo — o clipe continua
decorativo. Entrega valor sozinha, sem depender de OCR ou de qualquer outro
tipo de arquivo.

**Independent Test**: anexar um `.md` ou `.txt` com seções conhecidas,
perguntar sobre um trecho específico, e confirmar que a resposta cita a seção
e o trecho corretos, sem exigir nenhum outro tipo de arquivo implementado.

**Acceptance Scenarios**:

1. **Given** uma conversa aberta com o assistente, **When** a pessoa usa o
   clipe para anexar um `.md` ou `.txt`, **Then** a conversa mostra que o
   documento foi anexado e associado àquela conversa.
2. **Given** um documento anexado com seções distintas, **When** a pessoa
   pergunta sobre um assunto tratado numa seção específica, **Then** a
   resposta cita a seção e o trecho de origem daquela seção.
3. **Given** um documento anexado, **When** a pessoa faz uma pergunta cuja
   resposta está espalhada em seções distantes do documento, **Then** o
   assistente ainda localiza e cita os trechos relevantes de cada seção.
4. **Given** um documento anexado a uma conversa, **When** a pessoa abre uma
   conversa diferente e pergunta sobre o mesmo assunto, **Then** o assistente
   não usa o documento anexado na outra conversa como fonte.

---

### User Story 2 - Resposta honesta quando o documento não cobre a pergunta (Priority: P2)

A pessoa faz uma pergunta que o documento anexado não responde. O assistente
avisa que não encontrou evidência suficiente no documento em vez de inventar
uma resposta.

**Why this priority**: Sem essa garantia, a feature vira risco de
alucinação com aparência de autoridade (o usuário acha que a resposta veio do
documento quando não veio). É testável de forma independente da User Story 1,
mas depende dela existir para ter o que testar.

**Independent Test**: anexar um documento sobre assunto A, perguntar sobre
assunto B não coberto por ele, e confirmar que a resposta declara ausência de
evidência no documento, sem citar trecho nenhum.

**Acceptance Scenarios**:

1. **Given** um documento anexado sobre um assunto, **When** a pessoa
   pergunta sobre algo não coberto pelo documento, **Then** o assistente
   declara que não encontrou essa informação no documento anexado.
2. **Given** um documento anexado, **When** o documento contém instruções
   escritas como se fossem comandos para o assistente, **Then** o assistente
   trata esse conteúdo apenas como texto a ser citado, sem seguir instruções
   nele contidas.

---

### User Story 3 - Anexar PDF com extração de texto (Priority: P3)

A pessoa anexa um PDF (incluindo PDF escaneado, sem texto selecionável). O
assistente extrai o texto do arquivo antes de tratá-lo como fonte, e a
pessoa consegue perguntar sobre o conteúdo do PDF do mesmo jeito que faria com
um `.md` ou `.txt`.

**Why this priority**: Amplia o alcance da feature para o formato de
documento mais comum em uso real (manuais, relatórios, contratos), mas exige
uma etapa adicional de extração antes da árvore de recuperação — por isso
vem depois do núcleo em texto puro, que já entrega valor sozinho.

**Independent Test**: anexar um PDF com texto embutido e um PDF escaneado
(sem texto selecionável), perguntar sobre o conteúdo de cada um, e confirmar
que ambos produzem resposta citada equivalente à da User Story 1.

**Acceptance Scenarios**:

1. **Given** um PDF com texto selecionável, **When** a pessoa o anexa e
   pergunta sobre seu conteúdo, **Then** a resposta cita a seção/trecho de
   origem dentro do PDF.
2. **Given** um PDF escaneado sem texto selecionável, **When** a pessoa o
   anexa, **Then** o sistema extrai o texto antes de disponibilizá-lo como
   fonte, sem exigir ação manual da pessoa.
3. **Given** um PDF cuja extração de texto falha ou não produz texto
   aproveitável, **When** a pessoa pergunta sobre seu conteúdo, **Then** o
   assistente avisa que não conseguiu ler o documento, em vez de responder
   com base em outra fonte sem avisar.

---

### Edge Cases

- Arquivo maior que o tamanho máximo permitido: sistema rejeita o upload e
  explica o limite antes de gastar processamento.
- Extensão de arquivo fora das suportadas nesta rodada (ex.: `.docx`,
  imagem solta): sistema rejeita com mensagem clara sobre os formatos aceitos.
- Documento vazio ou sem conteúdo textual aproveitável: sistema avisa que não
  há conteúdo para usar como fonte.
- Duas pessoas com sessões diferentes anexam documentos na mesma janela de
  tempo: cada documento fica isolado por conversa, sem vazar para a outra.
- Conversa é arquivada ou excluída com documento anexado: o documento deixa
  de estar disponível como fonte junto com a conversa.
- Pessoa anexa um novo documento numa conversa que já tinha outro anexado:
  comportamento (substituir vs. acumular fontes) fica definido e previsível
  para quem usa.
- Upload enviado enquanto uma resposta anterior ainda está sendo gerada:
  sistema enfileira ou bloqueia o novo upload até liberar, sem corromper a
  resposta em andamento.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: O sistema DEVE permitir que a pessoa anexe um arquivo a partir
  do clipe já presente no compositor de mensagens da conversa com o
  assistente.
- **FR-002**: O sistema DEVE aceitar, nesta rodada, apenas arquivos de texto
  simples, Markdown e PDF, rejeitando qualquer outro formato com mensagem
  explicando os formatos aceitos.
- **FR-003**: O sistema DEVE recusar upload acima de um tamanho máximo
  definido, informando o limite à pessoa antes ou no momento do envio.
- **FR-004**: O sistema DEVE organizar o conteúdo do documento anexado numa
  estrutura hierárquica (raiz do documento → seções → subseções → trechos
  de origem), preservando a relação lógica entre partes do documento.
- **FR-005**: O sistema DEVE localizar o trecho relevante para uma pergunta
  navegando essa estrutura tanto da raiz em direção aos trechos quanto dos
  trechos em direção à raiz, de forma a reduzir conteúdo irrelevante enviado
  ao modelo.
- **FR-006**: Toda resposta baseada no documento anexado DEVE citar a
  seção/caminho hierárquico e o trecho de origem usados.
- **FR-007**: Quando não houver trecho do documento com evidência suficiente
  para responder, o sistema DEVE declarar explicitamente a ausência de
  evidência, sem produzir resposta inventada.
- **FR-008**: O sistema DEVE tratar o conteúdo do documento anexado como não
  confiável para fins de instrução — texto dentro do documento que se
  pareça com comando ao assistente DEVE ser tratado apenas como conteúdo a
  citar, nunca executado como instrução.
- **FR-009**: O documento anexado e sua estrutura DEVEM ficar restritos à
  conversa em que foram enviados, sem ficar disponíveis para busca a partir
  de outra conversa.
- **FR-010**: O documento anexado e sua estrutura NÃO DEVEM ser adicionados à
  base de conhecimento compartilhada usada pela busca de documentação interna
  já existente.
- **FR-011**: Para arquivos PDF sem texto selecionável, o sistema DEVE
  extrair o texto do arquivo antes de organizá-lo na estrutura hierárquica.
- **FR-012**: Quando a extração de texto de um PDF falhar ou não produzir
  conteúdo aproveitável, o sistema DEVE avisar a pessoa em vez de responder
  como se o documento estivesse disponível.
- **FR-013**: O sistema DEVE indicar visualmente, na conversa, que um
  documento está anexado e disponível como fonte.
- **FR-014**: O sistema DEVE remover o acesso ao documento anexado quando a
  conversa correspondente for excluída.

### Key Entities *(include if feature involves data)*

- **Documento Anexado**: representa o arquivo enviado numa conversa —
  nome do arquivo, tipo, tamanho, estado de processamento (recebido,
  processando, pronto, falhou) e a conversa à qual pertence. Existe apenas
  enquanto a conversa existir.
- **Nó da Estrutura Hierárquica**: representa uma unidade de conteúdo dentro
  do documento anexado (raiz, seção, subseção ou trecho-folha) — nível na
  hierarquia, nó pai, caminho/título e o texto ou resumo daquele nível.
- **Fonte Recuperada**: representa o resultado de uma busca dentro do
  documento anexado — caminho hierárquico de origem, trecho de texto citado
  e uma medida de relevância/distância usada para decidir se há evidência
  suficiente.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Uma pessoa consegue anexar um documento de texto/Markdown e
  receber uma primeira resposta citando trecho de origem em menos de 10
  segundos após enviar a pergunta.
- **SC-002**: 100% das respostas que usam o documento anexado como fonte
  citam a seção e o trecho de origem correspondentes.
- **SC-003**: Em um conjunto de perguntas de teste sem resposta no
  documento anexado, 100% das respostas declaram ausência de evidência em
  vez de inventar conteúdo.
- **SC-004**: Um documento anexado numa conversa nunca aparece como fonte em
  nenhuma outra conversa, verificado em teste com múltiplas conversas
  simultâneas.
- **SC-005**: Uma pessoa consegue anexar um PDF escaneado e receber resposta
  citável sobre seu conteúdo sem precisar converter o arquivo manualmente.

## Assumptions

- Esta feature amplia deliberadamente o escopo previamente registrado para o
  RAG local (que classificava OCR e PDF como fora do MVP inicial, dependentes
  de uma evolução futura). Aqui, a extração de texto de PDF enviado pela
  pessoa usuária é tratada como parte do fluxo desta feature — isolada por
  conversa —, não como uma mudança no pipeline de indexação compartilhada
  que atende à busca de documentação interna já existente.
- O documento anexado é efêmero: vale enquanto a conversa existir, não é
  promovido à base de conhecimento compartilhada, e não precisa de
  classificação de sensibilidade ou controle de acesso adicional além do já
  existente para a própria conversa.
- Um tamanho máximo de upload e um limite de tempo razoável para processar o
  documento existem, mas o valor exato é um detalhe de dimensionamento a
  definir na fase de planejamento, não uma decisão de escopo desta
  especificação.
- Quando uma pessoa anexa um novo documento numa conversa que já tinha outro,
  o novo documento substitui o anterior como fonte ativa daquela conversa
  (comportamento mais simples e previsível do que acumular múltiplas fontes
  sem indicação clara de qual está em uso).
- O restante da conversa (histórico de mensagens, favoritos, arquivamento)
  segue as regras já existentes para conversas do assistente; esta feature
  não altera esse comportamento.
