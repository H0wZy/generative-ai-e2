# Contrato — Navegação do shell (ícones, colapso, largura) — delta sobre specs/004 contracts/ui-v0-theme.md

## `frontend/src/lib/nav.ts`

**Adição**: novo export `NAV_ICONS: Record<string, LucideIcon>`, com o mesmo conteúdo que hoje vive em `conversation-sidebar.tsx` (`ICONS`, linhas 38-49) — ver `data-model.md` para a tabela rótulo→ícone completa. `NAV` e as funções existentes (`workspaceFor`, `useActiveWorkspace`, `sectionLabel`) não mudam de assinatura.

## `frontend/src/components/shell/sidebar.tsx`

Reescrito para o padrão da barra do Assistente, mantendo os mesmos dados de entrada (`NAV`, `useActiveWorkspace`) e o mesmo papel na árvore (`app/(shell)/layout.tsx` continua importando `Sidebar` sem mudar a assinatura do componente — sem props novas).

**Adições**:
- Ícone (`NAV_ICONS[item.label] ?? Home`) ao lado de cada rótulo de item, em qualquer estado (expandido, colapsado, mobile).
- Estado local `collapsed` (`useState<boolean>(false)`) e botão de colapsar/expandir, visível só em `md:` (ícones `PanelLeftClose`/`PanelLeftOpen` de `lucide-react`, mesmo padrão de `conversation-sidebar.tsx`).
- Largura fixa por estado em telas largas: `md:w-[280px]` (expandida) / `md:w-[68px]` (colapsada) — substitui o atual `md:w-56`. Abaixo de `md`, comportamento mobile inalterado (faixa horizontal `overflow-x-auto`, sem conceito de colapso).

**Sem mudança**: paleta (continua usando os tokens semânticos `bg-surface`/`text-text`/`bg-elevated`/`text-muted`/`bg-primary`/`text-primary-foreground`/`border-divider`/`outline-focus` já em uso desde a rodada 004 — ver research.md R2 para a equivalência de valor com os tokens `v0-*` do Assistente), breakpoint mobile/desktop (continua `md:`, 768px — o mesmo já usado hoje), lógica de item ativo (`pathname === item.href || pathname.startsWith(...)`), lógica do selo "em breve".

**Breakpoint do colapso**: usa o mesmo `md:` (768px) que já divide mobile/desktop no shell hoje, em vez de importar o `lg:` (1024px) que a `ConversationSidebar` do Assistente usa para seu próprio botão — evita introduzir um segundo breakpoint no shell só por paridade cosmética com o Assistente; nenhum FR desta rodada pede paridade de breakpoint exato entre as duas áreas, só o padrão visual/de interação (ícones, colapso, largura fixa).

## `frontend/src/components/shell/workspace-switcher.tsx`

**Sem mudança de contrato de token** — continua `bg-primary`/`text-primary-foreground` (já corrigido na rodada 004). Só precisa aceitar o layout colapsado do pai (ver Edge Cases do spec): quando `Sidebar` está colapsada, o `WorkspaceSwitcher` deixa de ser renderizado (mesma regra que `conversation-sidebar.tsx` já aplica ao próprio bloco de troca de workspace: `className={cn("px-4", collapsed && "lg:hidden")}`).

## `frontend/src/components/shell/topbar.tsx`

Ajuste de espaçamento/altura para bater com o cabeçalho do Assistente (`ai-assistant.tsx`, `<header className="flex items-center gap-3 border-b border-v0-border px-4 py-3 lg:px-6">`): troca `min-h-14 ... px-4` por `px-4 py-3 lg:px-6`, mesmo `border-b border-divider`. Conteúdo (`<h1>` com seção ativa + workspace) não muda.

## `frontend/src/components/assistant/conversation-sidebar.tsx`

**Sem mudança de comportamento** — só passa a importar `NAV_ICONS` de `@/lib/nav` em vez de manter seu próprio `ICONS` local (remove a duplicata; ver research.md R3).

## Consumidores não tocados

`frontend/src/app/(shell)/layout.tsx` não muda — continua montando `<Sidebar />` e `<Topbar />` sem props novas; a mudança de largura/ícones/colapso é inteiramente interna a `sidebar.tsx`. Nenhuma página de `frontend/src/app/(shell)/**` é editada nesta rodada (fora de escopo, spec Assumptions).
