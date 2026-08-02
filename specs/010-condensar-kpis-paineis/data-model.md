# Data Model: Densidade visual dos KPIs e gráficos

Sem entidade de dado — feature é só de apresentação sobre dados já
existentes (`Metrics`, `SprintDashboard`, `WorkflowListResponse`, já
consumidos por `(shell)/page.tsx` e `(shell)/agile/page.tsx`).

## Tokens de tamanho (antes → depois)

| Componente | Propriedade | Antes | Depois |
|---|---|---|---|
| `Stat` | padding do cartão | `p-4` | `p-3` |
| `Stat` | tamanho do valor | `text-2xl` | `text-xl` |
| `Card` | padding | `p-4` | `p-3` |
| `Card` | `CardHeader` margem inferior | `mb-3` | `mb-2` |
| `Donut` | `size` default (px) | `140` | `104` |
| `Burndown` | `height` default (px) | `160` | `120` |
| Grid de indicadores (`page.tsx`, `agile/page.tsx`) | `gap` | `gap-3` | `gap-2` |
| Grid de cartões de gráfico | `gap` | `gap-4` | `gap-3` |

Nenhuma prop nova obrigatória — `size`/`height` continuam com default,
chamadores existentes que não passam valor explícito herdam o novo
tamanho automaticamente.
