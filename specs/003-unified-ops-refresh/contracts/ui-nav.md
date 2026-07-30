# Contrato — Navegação e identidade visual

## `frontend/src/lib/nav.ts`

**Remoção**: item `{ label: "Reports", href: "/reports", ... }` sai dos dois arrays (`itsm` e `agile`) de `NAV`. Rota `/reports` deixa de existir (`frontend/src/app/reports/` removido).

**`workspaceFor()` — fix (FR-056)**:

```ts
// Antes — qualquer rota fora de /agile cai em "itsm" por padrão
export function workspaceFor(pathname: string): Workspace {
  return pathname.startsWith("/agile") ? "agile" : "itsm";
}
```

Depois de remover Reports, toda rota compartilhada que sobra (`/`, `/assistant`, `/em-construcao/*`) precisa **preservar** o workspace atual em vez de assumir ITSM. Como `workspaceFor` é uma função pura de `pathname` — sem acesso ao workspace anterior — o fix move a decisão para o componente que já tem o estado anterior (`Sidebar`, via `usePathname` mais o workspace do render anterior), não para a função pura: rotas não prefixadas por `/agile` nem `/itsm` deixam de forçar `"itsm"` e passam a manter o último workspace ativo (estado local do `Sidebar`, inicializado por `/itsm` como hoje). `workspaceFor` continua determinística para os dois casos inequívocos (`/agile/*` ⇒ agile, `/itsm/*` ⇒ itsm); o terceiro caso ("nem um nem outro") deixa de ter uma resposta fixa própria.

## `frontend/src/app/globals.css` — tokens (delta sobre specs/002 research.md R9)

| Token | Valor atual (specs/002) | Valor novo |
|---|---|---|
| `--color-bg` (escuro) | `#161826` | `#141414` |
| `--color-surface` (escuro) | `#232532` | `#1c1c1c` |
| `--color-divider` (escuro) | mix de `#e9e9ed` | mix de `#333331` |
| `--color-text` (escuro) | `#e9e9ed` | `#edebe6` |
| `--color-accent` | `#9184d9` (roxo) | `#c9a227` (brass) |
| status ok/warn/crítico | não existiam como tokens dedicados | `#5e9c76` / `#d98a3d` / `#c24a3f` |

Rampas `--color-neutral-*` e `--color-accent-*` (100–900) são recalculadas a partir dos novos valores-base, mantendo a mesma estrutura de 9 degraus — nenhum componente referencia hex, todos usam `text-text`/`bg-surface`/`text-accent-*` etc.

**Tema claro**: os pares precisam ser remedidos (contraste AA, 4.5:1) com os hex novos — não é herdado do tema escuro automaticamente (mesma disciplina de specs/002 FR-008/SC-005).

## Trilho de status — reuso de `Tag`, não componente novo

`frontend/src/components/ui/tag.tsx` (`Tag tone="danger"|"success"|...`) já é o padrão de indicador por status usado em `/itsm/[id]`. FR-055 pede o mesmo indicador em toda lista/card — a extensão é aplicar uma borda de 3px (`border-l-[3px]`) na cor do `tone` já resolvido pelo `Tag`, na `TicketTable` e nos cards de Kanban/Scrum, em vez de badge solto. Nenhum componente novo — só a classe de borda condicionada ao mesmo `tone`.
