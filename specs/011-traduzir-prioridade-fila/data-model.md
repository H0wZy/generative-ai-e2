# Data Model: Tradução de prioridade

Sem entidade de dado nova — `Ticket.priority` (tipo já existente em
`lib/types.ts`) não muda de forma nem de valor armazenado/transmitido.

## Novo módulo: `lib/ticket-priority.ts`

```ts
export const PRIORITY_LABELS: Record<string, string> = {
  urgent: "Urgente",
  high: "Alta",
  medium: "Média",
  low: "Baixa",
};

export const PRIORITY_OPTIONS = [
  ["", "Todas as prioridades"],
  ["urgent", "Urgente"],
  ["high", "Alta"],
  ["medium", "Média"],
  ["low", "Baixa"],
] as const;
```

- `PRIORITY_LABELS`: usado onde só se precisa do rótulo de um valor
  conhecido (badge da tabela, campo de detalhe).
- `PRIORITY_OPTIONS`: usado onde se precisa da lista completa com a opção
  "todas" (o `<Select>` do filtro) — mantém a forma que
  `ticket-filters.tsx` já espera hoje, só movendo a origem do array.

## Pontos de consumo

| Arquivo | Antes | Depois |
|---|---|---|
| `ticket-filters.tsx` | `PRIORITY_OPTIONS` local | importa de `lib/ticket-priority` |
| `ticket-table.tsx` | `{item.ticket.priority}` cru | `{PRIORITY_LABELS[item.ticket.priority] ?? item.ticket.priority}` |
| `itsm/[id]/page.tsx` | `{detail.ticket.priority}` cru | `{PRIORITY_LABELS[detail.ticket.priority] ?? detail.ticket.priority}` |

O valor bruto (`item.ticket.priority`, `detail.ticket.priority`) continua
sendo passado sem alteração para filtro, ordenação e
`ticket-edit-panel.tsx` (formulário de edição) — só o texto renderizado
para leitura muda.
