# Feature Specification: Normalização de squads exibidas (Squad1–Squad8)

**Feature Branch**: `012-normalizar-squads`

**Created**: 2026-08-02

**Status**: Draft

**Input**: User description: "sobre os squads: deixe apenas Squad1-Squad8, platform, identity etc não são squads."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Só squads canônicas aparecem na interface (Priority: P1)

Como analista consultando a fila de tickets ou os filtros por squad, quero
ver apenas os oito squads oficiais (Squad1 a Squad8), para não ver nomes
legados como "platform", "identity", "finance" ou "Squad4" (formato antigo)
misturados com os nomes atuais, o que sugere squads que não existem mais na
organização.

**Why this priority**: é a informação usada para filtrar e entender de
quem é a responsabilidade de um ticket — nomes legados nesse campo
confundem o usuário sobre a estrutura real de squads hoje.

**Independent Test**: abrir a fila de tickets, olhar a coluna Squad de
cada linha e a lista de opções do filtro de squad — nenhum valor fora do
conjunto Squad1–Squad8 deve aparecer.

**Acceptance Scenarios**:

1. **Given** a fila de tickets tem execuções antigas com squad registrada
   como "platform", "identity", "finance" ou "Squad4" (nomenclatura
   legada), **When** a coluna Squad é renderizada, **Then** o valor
   exibido é o squad canônico correspondente no formato "Squad1".."Squad8",
   nunca o nome legado.
2. **Given** o usuário abre o filtro de squad na fila de tickets, **When**
   a lista de opções é montada, **Then** ela contém apenas squads no
   formato canônico "Squad1".."Squad8", sem duplicar o mesmo squad em dois
   formatos diferentes.
3. **Given** um ticket tem squad ausente (não roteado ainda / revisão
   humana), **When** exibido na fila, **Then** continua mostrando "—"
   (comportamento atual, não é afetado por esta spec).

---

### User Story 2 - Consistência entre exibição e roteamento (Priority: P2)

Como responsável por manter o pipeline de roteamento, quero que o rótulo
exibido na interface reflita exatamente o mesmo squad usado internamente
para decidir o roteamento (Squad1↔squad canônico interno), para que um
usuário não veja um nome na tela e outro nos logs/relatórios internos.

**Why this priority**: consistência interna — menor prioridade que a P1
porque não afeta diretamente a experiência do usuário final, mas evita
divergência futura entre exibição e dado operacional.

**Independent Test**: comparar o squad mostrado na fila com o squad
registrado internamente para a mesma execução (via ferramenta de suporte já
existente) e confirmar que ambos apontam para o mesmo squad canônico.

**Acceptance Scenarios**:

1. **Given** uma execução tem squad canônico interno "Squad3", **When**
   exibida na interface, **Then** o rótulo mostrado é exatamente "Squad3".
2. **Given** um novo ticket é roteado a partir de agora, **When** a squad é
   determinada pelo pipeline, **Then** o valor gravado e o valor exibido
   já nascem no formato canônico, sem depender de tradução adicional na
   tela.

---

### Edge Cases

- Execução histórica cuja squad legada não corresponde a nenhum squad
  canônico atual (ex. um nome de squad real do cliente que nunca existiu no
  conjunto de 8 genéricos): exibir um estado neutro ("—" ou "squad não
  identificada") em vez de inventar um mapeamento incorreto.
- Squad canônica já vem corretamente formatada (ex. já é "Squad4" no
  formato novo): não deve haver dupla tradução nem erro.
- Filtro de squad usado numa URL compartilhada com o formato antigo (ex.
  `?squad=platform`): o sistema deve tratar de forma previsível — não
  quebrar a busca, mesmo que não haja mais resultado para esse valor.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: A interface DEVE exibir squads exclusivamente no formato
  canônico "Squad1" a "Squad8" em qualquer coluna, selo ou filtro que
  mostre a squad de um ticket.
- **FR-002**: Valores de squad legados presentes em execuções históricas
  ("platform", "identity", "finance", "Squad4" em formato antigo, e
  equivalentes) DEVEM ser mapeados para o squad canônico correspondente ao
  serem exibidos, ou tratados como squad desconhecida quando não houver
  correspondência clara.
- **FR-003**: A lista de opções do filtro de squad DEVE ser construída a
  partir do conjunto canônico de squads presentes nos dados, sem exibir o
  mesmo squad duas vezes em formatos diferentes.
- **FR-004**: O pipeline de roteamento DEVE continuar gravando apenas
  squads do conjunto canônico para toda nova execução — este requisito
  formaliza o comportamento que a normalização de roteamento já busca
  hoje, garantindo que não haja regressão.
- **FR-005**: Quando uma squad não corresponde a nenhum valor canônico
  conhecido, a interface DEVE mostrar um estado neutro explícito (ex. "—"
  ou rótulo equivalente ao já usado para squad ausente), nunca um valor
  legado cru.

### Key Entities

- **Squad canônica**: um dos oito squads oficiais (Squad1 a Squad8) usados
  para roteamento e exibição.
- **Squad legada**: valor histórico anterior à padronização atual
  (ex. "platform", "identity", "finance", "Squad4" sem formatação), presente
  em execuções antigas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% dos valores de squad exibidos na fila de tickets e no
  filtro de squad pertencem ao conjunto Squad1–Squad8 ou ao estado neutro
  de "sem squad".
- **SC-002**: Zero ocorrências de "platform", "identity", "finance" ou
  variações de formatação antiga visíveis na interface após a
  implementação.
- **SC-003**: O filtro de squad não lista o mesmo squad mais de uma vez.

## Assumptions

- O conjunto canônico de 8 squads e a lógica de normalização
  (`normalize_squad`) já existem no backend para fins de roteamento; esta
  spec estende essa mesma normalização para o que é exibido na interface e
  cobre a limpeza/mapeamento de dados históricos, sem introduzir um novo
  conceito de squad.
- O formato de exibição usado é "Squad1".."Squad8" (conforme pedido
  explicitamente pelo usuário), podendo divergir do formato interno
  ("SQUAD-01") usado em roteamento — a spec cobre a camada de
  apresentação, não exige renomear o identificador interno.
- Execuções históricas cujo squad legado não tem mapeamento óbvio para um
  dos 8 squads atuais (ex. dado real de cliente que nunca fez parte do
  conjunto genérico) são tratadas como "sem squad" na exibição — não é
  papel desta spec inventar uma correspondência arbitrária.
