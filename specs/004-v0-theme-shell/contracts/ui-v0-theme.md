# Contrato — Tokens de tema e shell (delta sobre specs/003 contracts/ui-nav.md)

## `frontend/src/app/globals.css`

**Tokens — valor substituído (nome mantido, ver `data-model.md` para lista completa)**:

| Token | Valor atual (specs/003) | Valor novo (v0, oklch literal de `.v0-assistant`) |
|---|---|---|
| `--color-bg` | `#141414` | `oklch(0.145 0 0)` |
| `--color-surface` | `#1c1c1c` | `oklch(0.205 0 0)` |
| `--color-text` | `#edebe6` | `oklch(0.985 0 0)` |
| `--color-muted` | `var(--color-neutral-500)` | `oklch(0.708 0 0)` |
| `--color-link` | `var(--color-accent-300)` | `oklch(0.708 0 0)` |
| `--color-focus` | `var(--color-accent-400)` | `oklch(0.556 0 0)` |
| `--color-primary` | `var(--color-accent-700)` | `oklch(0.922 0 0)` |
| `--color-primary-hover` | `var(--color-accent-800)` | `oklch(0.85 0 0)` |
| `--color-elevated` | `var(--color-neutral-900)` | `oklch(0.269 0 0)` |
| `--color-divider` | mix `#333331` 16% | `oklch(1 0 0 / 10%)` |

**Tokens novos**:

| Token | Valor | Papel |
|---|---|---|
| `--color-destructive` | `oklch(0.704 0.191 22.216)` | Texto/ícone de ação destrutiva (excluir, etc). **Regra de uso** (R2 em `research.md`): nunca como fundo sólido com texto claro por cima — só como texto próprio, ou fundo tinturado (`/15` ou similar) com o mesmo tom como texto. |
| `--color-primary-foreground` | `oklch(0.205 0 0)` | Texto sobre `bg-primary` (era resolvido ad-hoc via `text-neutral-100`; passa a ter nome próprio, mesmo padrão de `ui-primary` do restante do produto). |

**Removidos**:
- Bloco `:root[data-theme="light"]` inteiro (`globals.css:80-95`).
- `--color-status-ok`, `--color-status-warn`, `--color-status-critical`: **sem mudança** — fora deste contrato, trilho de status não muda.

**Expostos no `@theme inline`**: `--color-destructive` e `--color-primary-foreground` entram no bloco `@theme inline` (`globals.css:97-151`) junto aos demais tokens semânticos, para existir como utilitário Tailwind (`text-destructive`, `bg-destructive`, `text-primary-foreground`) em qualquer componente do produto, não só shell.

## `frontend/src/app/layout.tsx`

Script anti-FOUC (`themeInitScript`, linhas 18-22, e a tag `<script>` na linha 32) **removido** — não há mais `data-theme` para aplicar antes da pintura; o produto é dark-only, sem estado de tema para ler de `localStorage`.

## `frontend/src/components/shell/theme-toggle.tsx`

**Arquivo removido.** Nenhum outro componente o importa fora de `topbar.tsx` (confirmado antes da remoção).

## `frontend/src/components/shell/topbar.tsx`

Remove import e uso de `<ThemeToggle />` (linha 7 e 23). Estrutura do `<header>` e do `<h1>` de título permanece — só o botão de alternância de tema sai do lado direito.

## `frontend/src/components/shell/sidebar.tsx` e `workspace-switcher.tsx`

**Sem mudança de contrato** — nenhuma classe Tailwind referenciada por esses dois componentes muda de nome; só o valor por trás de cada token muda (ver tabela acima). É a prova de que FR-001 e FR-004 se cumprem sem editar estes arquivos além do necessário.

## Consumidores herdados (não editados nesta rodada, confirmação de herança — FR-004, FR-009)

`frontend/src/components/ui/{button,card,table,tag,stat,skeleton,empty-state,error-state,unavailable-state}.tsx` e toda tela de `frontend/src/app/(shell)/**` — nenhum arquivo aqui é tocado; todos resolvem os tokens acima por nome de classe Tailwind (`bg-surface`, `text-muted`, `bg-primary`, `border-divider`, ...), confirmados por busca prévia sem nenhuma cor hardcoded nesses componentes.
