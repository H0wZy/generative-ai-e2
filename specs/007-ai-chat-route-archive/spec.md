# Feature Specification: Rota por conversa e arquivamento de conversas

**Feature Branch**: `007-ai-chat-route-archive`

**Created**: 2026-08-01

**Status**: Completed

**Input**: User description: "Rodada 007: rota /ai/chat/{id} + arquivar (migration 008), API intocada, sem compartilhamento. Fecha o que você quer e não abre frente nova. Não vamos tocar no rename da api, deixe de fora, apenas ajustar a url do frontend."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cada conversa tem endereço próprio (Priority: P1)

Ao abrir uma conversa, o endereço na barra do navegador passa a identificar
aquela conversa especificamente. Voltar e avançar no navegador percorre as
conversas visitadas. Recarregar a página reabre a mesma conversa. Guardar o
endereço nos favoritos do navegador e voltar depois reabre a mesma conversa.

**Why this priority**: É a base de tudo o mais nesta rodada. Sem endereço
próprio, excluir e arquivar não têm alvo explícito, o botão voltar do navegador
sai da tela do assistente inteira em vez de voltar à conversa anterior, e
recarregar perde o contexto. Sozinha já entrega valor.

**Independent Test**: abrir duas conversas em sequência, conferir que o endereço
muda a cada uma, apertar voltar e confirmar que retorna à anterior (não à tela
inicial), recarregar e confirmar que a conversa continua aberta.

**Acceptance Scenarios**:

1. **Given** a lista de conversas, **When** a pessoa abre uma conversa,
   **Then** o endereço passa a conter o identificador daquela conversa.
2. **Given** uma conversa aberta, **When** a página é recarregada, **Then** a
   mesma conversa reabre com todo o histórico.
3. **Given** duas conversas abertas em sequência, **When** a pessoa usa o botão
   voltar do navegador, **Then** retorna à conversa anterior.
4. **Given** o endereço de uma conversa guardado, **When** aberto numa aba nova
   da mesma sessão, **Then** a conversa abre normalmente.
5. **Given** uma conversa nova ainda sem nenhuma mensagem, **When** a pessoa
   envia a primeira pergunta, **Then** o endereço passa a identificar a conversa
   recém-criada, sem recarregar a página nem perder a resposta em andamento.
6. **Given** um endereço de conversa que não existe ou pertence a outra sessão,
   **When** acessado, **Then** a tela explica que a conversa não foi encontrada
   e oferece caminho para iniciar uma nova.

---

### User Story 2 - Arquivar conversa (Priority: P2)

A pessoa arquiva conversas que não quer mais ver na navegação do dia a dia, sem
perdê-las. Conversas arquivadas somem de "Favoritos" e "Recentes", continuam
existindo e podem ser consultadas e desarquivadas.

**Why this priority**: resolve o acúmulo na barra lateral sem obrigar a
escolher entre "conviver com a bagunça" e "excluir para sempre". Depende da US1
apenas por conveniência (o alvo fica explícito), mas é testável sozinha.

**Independent Test**: arquivar uma conversa, confirmar que sai das listas
ativas, encontrá-la na lista de arquivadas, desarquivar e confirmar que volta ao
lugar de origem.

**Acceptance Scenarios**:

1. **Given** uma conversa nas listas ativas, **When** a pessoa arquiva,
   **Then** ela some de "Favoritos" e "Recentes" e passa a aparecer entre as
   arquivadas.
2. **Given** uma conversa arquivada, **When** a pessoa desarquiva, **Then** ela
   volta à lista de origem — "Favoritos" se estava favoritada, "Recentes" caso
   contrário.
3. **Given** uma conversa favoritada, **When** arquivada, **Then** continua
   marcada como favorita, apenas fora das listas ativas.
4. **Given** a conversa aberta na tela, **When** ela é arquivada, **Then** a
   tela continua utilizável e informa que a conversa está arquivada.
5. **Given** uma conversa arquivada, **When** acessada pelo endereço direto,
   **Then** abre normalmente, com aviso de que está arquivada.
6. **Given** uma conversa arquivada, **When** a pessoa exclui, **Then** a
   exclusão funciona igual à de uma conversa ativa, com a mesma janela de
   desfazer.
7. **Given** nenhuma conversa arquivada, **When** a pessoa abre a lista de
   arquivadas, **Then** vê uma mensagem de lista vazia, não um espaço em branco.

---

### User Story 3 - Endereços antigos continuam funcionando (Priority: P3)

Quem tiver o endereço antigo da tela do assistente guardado — nos favoritos do
navegador, num histórico ou colado em algum lugar — continua chegando ao lugar
certo.

**Why this priority**: evita quebrar o que já circula. Baixo esforço, e sem isso
a mudança de endereço vira regressão para quem já usa.

**Independent Test**: acessar o endereço antigo, com e sem identificador de
conversa, e confirmar que chega ao destino equivalente no formato novo.

**Acceptance Scenarios**:

1. **Given** o endereço antigo da tela do assistente sem conversa específica,
   **When** acessado, **Then** a pessoa chega à tela de conversa nova.
2. **Given** o endereço antigo com um identificador de conversa,
   **When** acessado, **Then** a pessoa chega àquela conversa no endereço novo.
3. **Given** qualquer um desses acessos, **When** a página termina de carregar,
   **Then** a barra de endereço mostra o formato novo, não o antigo.

---

### Edge Cases

- Identificador malformado no endereço: mesma resposta de conversa inexistente,
  sem tela de erro técnica.
- Conversa aberta em duas abas e excluída numa delas: a outra aba, ao ser usada,
  informa que a conversa não existe mais em vez de falhar silenciosamente.
- Conversa arquivada e excluída dentro da janela de desfazer: desfazer devolve a
  conversa ao estado arquivado, não ao ativo.
- Última conversa da lista arquivada: a lista de arquivadas passa a exibir o
  estado vazio.
- Pessoa envia pergunta e navega para outra conversa antes da resposta chegar: a
  resposta pertence à conversa de origem e não aparece na que está aberta.
- Endereço de conversa aberto em outro navegador ou sessão: tratado como
  inexistente (ver FR-013).

## Requirements *(mandatory)*

### Functional Requirements

**Endereço por conversa**

- **FR-001**: Cada conversa MUST ser endereçável por um endereço único e estável
  que contenha seu identificador.
- **FR-002**: Abrir uma conversa MUST refletir a mudança no endereço do
  navegador, criando entrada no histórico de navegação.
- **FR-003**: Recarregar o endereço de uma conversa MUST reabrir aquela conversa
  com o histórico completo.
- **FR-004**: Voltar e avançar no navegador MUST percorrer as conversas
  visitadas.
- **FR-005**: Uma conversa nova, ainda sem mensagens, MUST ter endereço próprio
  distinto do de qualquer conversa existente.
- **FR-006**: Ao enviar a primeira pergunta numa conversa nova, o endereço MUST
  passar a identificar a conversa criada, sem recarregar a página e sem
  interromper a resposta em andamento.
- **FR-007**: Endereço com identificador inexistente, malformado ou pertencente
  a outra sessão MUST levar a uma tela que explica a ausência e oferece iniciar
  nova conversa.

**Arquivar**

- **FR-008**: Toda conversa MUST poder ser arquivada e desarquivada.
- **FR-009**: Conversa arquivada MUST sumir de "Favoritos" e de "Recentes".
- **FR-010**: Conversa arquivada MUST permanecer acessível por lista própria e
  por endereço direto.
- **FR-011**: Arquivar MUST NOT alterar a marcação de favorita — desarquivar
  devolve a conversa à lista correspondente ao estado que ela já tinha.
- **FR-012**: O sistema MUST registrar o momento em que cada conversa foi
  arquivada.
- **FR-013**: Excluir MUST continuar funcionando igual para conversa arquivada,
  com a mesma janela de desfazer; desfazer devolve ao estado arquivado.

**Privacidade e limites**

- **FR-014**: O endereço de uma conversa MUST ser válido somente para a sessão
  dona; qualquer outra sessão recebe o mesmo tratamento de conversa inexistente.
- **FR-015**: A interface MUST NOT oferecer ação de copiar ou compartilhar o
  endereço de uma conversa, para não sugerir um compartilhamento que o sistema
  não suporta.

**Compatibilidade**

- **FR-016**: O endereço anterior da tela do assistente MUST continuar levando
  ao destino equivalente no formato novo, com e sem identificador de conversa.
- **FR-017**: Após o redirecionamento, a barra de endereço MUST exibir o formato
  novo.

### Key Entities

- **Conversa**: já existe. Ganha o registro do momento de arquivamento, que
  distingue conversa ativa de arquivada. Continua pertencendo a uma sessão,
  tendo título, marcação de favorita e datas de criação e atualização.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% das conversas abertas produzem um endereço distinto que,
  colado numa aba nova da mesma sessão, reabre exatamente a mesma conversa.
- **SC-002**: Após visitar 3 conversas em sequência, o botão voltar retorna à
  conversa imediatamente anterior nas 3 vezes.
- **SC-003**: Recarregar o endereço de uma conversa reabre o histórico completo,
  sem perda de mensagens, em 100% das tentativas.
- **SC-004**: Conversa arquivada não aparece em "Favoritos" nem em "Recentes" e
  aparece na lista de arquivadas — verificável em uma passagem.
- **SC-005**: Desarquivar devolve a conversa à lista de origem correta
  (favoritada ou recente) em 100% dos casos testados.
- **SC-006**: Nenhum endereço de conversa acessado por outra sessão expõe
  título, mensagens ou qualquer indício de que a conversa existe.
- **SC-007**: Nenhuma tela oferece copiar ou compartilhar endereço de conversa.
- **SC-008**: Os endereços do formato antigo continuam chegando ao destino
  equivalente, verificado com e sem identificador de conversa.
- **SC-009**: A verificação de tipos, o linter e a suíte de testes do backend
  permanecem sem erro novo.

## Assumptions

- **A-001**: "API intocada" significa **não renomear** o prefixo das rotas de
  assistente. Arquivar exige uma coluna nova na conversa e um campo novo no
  endpoint de atualização que já existe — isso é extensão do contrato atual, não
  renomeação, e está dentro do escopo.
- **A-002**: A conversa nova permanece criada de forma preguiçosa: só vira
  registro no servidor na primeira pergunta enviada. O endereço da conversa
  ainda não persistida usa um marcador fixo, distinto de qualquer identificador
  real, e é substituído pelo endereço definitivo quando ela passa a existir.
  Criar a conversa no servidor já na abertura encheria "Recentes" de conversas
  vazias — comportamento que a rodada anterior evitou de propósito.
- **A-003**: Arquivada e favorita são estados independentes. As listas ativas
  filtram por "não arquivada"; a lista de arquivadas ignora a marcação de
  favorita.
- **A-004**: A lista de arquivadas é um destino próprio na navegação, não uma
  seção sempre visível na barra lateral — o objetivo do arquivamento é
  justamente tirar essas conversas do caminho.
- **A-005**: Sem compartilhamento, sem contas e sem login nesta rodada. O
  endereço continua privado por sessão, exatamente como o comportamento atual.
- **A-006**: Sem exclusão em massa, sem arquivamento automático por idade e sem
  busca dentro das arquivadas.

## Dependencies

- **D-001**: Depende do identificador único por conversa e da posse por sessão
  que já existem no modelo de dados atual — esta rodada usa o que está lá, não
  cria identidade nova.
- **D-002**: Depende da janela de desfazer entregue na rodada 006, reaproveitada
  para exclusão de conversa arquivada.

## Out of Scope

- Renomear o prefixo das rotas de assistente para "ai" no servidor.
- Compartilhar conversa com outra pessoa, por link público ou por convite.
- Contas, login ou qualquer identidade além da sessão do navegador.
- Envio de arquivos para análise do modelo — pedido explicitamente para a
  rodada seguinte.
- Busca, filtro ou ordenação dentro da lista de arquivadas.
- Arquivamento automático por tempo de inatividade.
- Exportar conversa.
