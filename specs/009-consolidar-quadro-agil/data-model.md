# Data Model: Quadro único e drag-and-drop confiável

Sem entidade de dado nova nem mudança de schema — a feature é de UI e
roteamento sobre dados já existentes via `/api/v1/agile/board`.

## Estado de UI (client-side, não persistido)

### Escopo do quadro

- Valores: `"sprint"` | `"board"`.
- Fonte: querystring `?escopo=` da rota `/agile/quadro` (server component
  lê e escolhe o `scope` passado a `apiFetch`); alterado no cliente via
  `router.replace` (mesmo padrão já usado em `ticket-filters.tsx`).
- Default: `"sprint"` quando ausente (equivalente ao antigo padrão de
  `/agile/scrum` ser o link primário no painel).

### Estado de arrasto (`DragState`, já existe em `board.tsx`)

- `{ key: string; from: string } | null` — sem mudança de forma; ganha um
  companheiro `dragOverColumn: string | null` para o indicador visual de
  destino (Decisão 3 do research.md).

## Redirects

| Rota antiga | Redirect para |
|---|---|
| `/agile/scrum` | `/agile/quadro?escopo=sprint` |
| `/agile/kanban` | `/agile/quadro?escopo=board` |

Redirect é server-side (`redirect()` do Next.js), mesmo padrão já usado em
`frontend/src/app/assistant/page.tsx` para a rota antiga do Assistente.
