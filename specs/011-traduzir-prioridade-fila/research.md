# Research: Tradução de prioridade

## Decisão 1 — Módulo compartilhado vs. duplicar a tabela

**Decision**: extrair `PRIORITY_LABELS`/`PRIORITY_OPTIONS` para
`frontend/src/lib/ticket-priority.ts`, consumido pelos 3 pontos que
exibem prioridade (filtro, badge da lista, campo de detalhe).

**Rationale**: o bug relatado existe exatamente porque a tradução foi
escrita uma vez (`ticket-filters.tsx`) e não reaproveitada — duplicar de
novo em `ticket-table.tsx` e `[id]/page.tsx` reproduziria o mesmo risco
pela terceira e quarta vez. Diferente do caso de `STATUS`
(duplicado hoje entre `ticket-table.tsx` e `ticket-filters.tsx` sem bug
aparente, porque cada cópia inclui além do rótulo dados exclusivos de
UI — tom de badge, trilho de cor —, então não é *pura* duplicação), aqui
o dado é literalmente o mesmo mapa string→string nos 3 lugares, sem
informação adicional específica de cada tela — caso claro de extrair.

**Alternatives considered**:
- Copiar o objeto `PRIORITY_TONE`-like em cada arquivo (mesmo padrão do
  `STATUS` local hoje): rejeitado porque é exatamente a causa do bug
  original — a tradução já existia num lugar e não foi propagada.
- Unificar também `STATUS` neste módulo: fora de escopo desta spec (que é
  sobre prioridade); mudar `STATUS` sem necessidade aqui seria escopo
  além do pedido.

## Decisão 2 — Fallback para valor desconhecido

**Decision**: `PRIORITY_LABELS[priority] ?? priority` — se a prioridade
não estiver no mapa, mostra o valor original em vez de "—" ou string
vazia.

**Rationale**: FR-004 da spec exige que um valor fora do conjunto
conhecido continue visível, não seja ocultado — mesmo padrão defensivo já
usado em `PRIORITY_TONE[item.ticket.priority] ?? "neutral"` (linha 65 de
`ticket-table.tsx` hoje, só para o tom da cor, não para o texto).
