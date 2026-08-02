# Data Model: Navegação do shell com ícones, colapso e largura estável

Feature é puramente de apresentação (frontend) — sem entidade persistida, sem chamada de API nova. As "entidades" abaixo são estruturas de UI já existentes ou pequenas adições diretamente derivadas do spec (`Key Entities`).

## NavItem (existente, sem mudança de forma)

Definido em `frontend/src/lib/nav.ts`. Não muda nesta rodada — rótulo, destino e status `implemented` continuam os mesmos (spec, Assumptions).

| Campo | Tipo | Origem |
|---|---|---|
| `label` | `string` | já existente |
| `href` | `string` | já existente |
| `implemented` | `boolean` | já existente |

## NAV_ICONS (novo — lookup, não é dado de negócio)

`Record<string, LucideIcon>` movido de `conversation-sidebar.tsx` para `frontend/src/lib/nav.ts`, chaveado pelo mesmo `label` usado em `NAV`. Fallback para `Home` quando um rótulo não tem entrada mapeada (mesma regra que `conversation-sidebar.tsx` já usa hoje: `ICONS[item.label] ?? Home`).

| Rótulo (`NavItem.label`) | Ícone (`lucide-react`) |
|---|---|
| Home | `Home` |
| Dashboard | `LayoutDashboard` |
| Assets | `Boxes` |
| Base de Conhecimento | `BookOpen` |
| Automações | `Workflow` |
| Assistente de IA | `Sparkles` |
| Administração | `Settings` |
| Backlog | `ListTodo` |
| Quadro Scrum | `KanbanSquare` |
| Quadro Kanban | `Blocks` |

## Estado de colapso da barra lateral (novo — estado de UI local)

Local ao componente `Sidebar` do shell (não persiste, não é dado de negócio — spec, Key Entities e Edge Cases).

| Campo | Tipo | Regra |
|---|---|---|
| `collapsed` | `boolean` (useState, default `false`) | Alternado só pelo botão de colapsar, visível só em `md:` (telas largas — mesmo breakpoint que o shell já usa hoje para mobile/desktop). Não afeta o layout mobile (faixa horizontal), que não tem conceito de colapso. |

Larguras resultantes (fixas, não dependem do conteúdo de `<main>` — ver research.md R1/R2):

| Estado | Largura (`md:` e acima) |
|---|---|
| Expandida (`collapsed = false`) | `280px` |
| Colapsada (`collapsed = true`) | `68px` |
