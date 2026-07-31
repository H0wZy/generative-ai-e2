# Data Model: Unificação visual v0 — fundação de tokens + shell

Não há entidade de dado persistido nesta feature (é puramente visual). A "entidade" relevante é o **Token de design** — cada variável CSS em `:root` que um componente consome por nome, nunca por valor literal.

## Entidade: Design Token

| Campo | Descrição |
|---|---|
| `name` | Nome do custom property (`--color-bg`, `--color-elevated`, ...) — estável, não muda nesta rodada. |
| `previous_value` | Valor ink/brass anterior (hex). |
| `new_value` | Valor v0 novo (oklch, copiado literal de `.v0-assistant`). |
| `consumers` | Componentes/classes Tailwind que resolvem esse nome hoje (ex.: `bg-surface` → `sidebar.tsx`, `card.tsx`, ...). Não muda — é a garantia de herança sem edição de JSX. |
| `contrast_pair` | Outro token que forma par texto/fundo com este, e a razão WCAG medida (ver `research.md` R2). |
| `status` | `renamed` (valor trocado, nome mantido) \| `new` (token não existia antes) \| `removed` (deixa de existir, ex.: bloco `[data-theme="light"]` inteiro). |

## Instâncias

| name | previous_value | new_value | status |
|---|---|---|---|
| `--color-bg` | `#141414` (já era este valor — spec 003 já tinha alinhado) | `oklch(0.145 0 0)` | renamed |
| `--color-surface` | `#1c1c1c` | `oklch(0.205 0 0)` | renamed |
| `--color-text` | `#edebe6` | `oklch(0.985 0 0)` | renamed |
| `--color-muted` | `var(--color-neutral-500)` (`#8f8b82`) | `oklch(0.708 0 0)` | renamed |
| `--color-link` | `var(--color-accent-300)` | `oklch(0.708 0 0)` (mesmo tom de `muted` — v0 não tem cor de link distinta; ver nota abaixo) | renamed |
| `--color-focus` | `var(--color-accent-400)` | `oklch(0.556 0 0)` (= `ring` do v0) | renamed |
| `--color-primary` | `var(--color-accent-700)` | `oklch(0.922 0 0)` | renamed |
| `--color-primary-hover` | `var(--color-accent-800)` | `oklch(0.85 0 0)` (leve escurecida sobre `primary`, mesma lógica de hover do resto do produto) | renamed |
| `--color-elevated` | `var(--color-neutral-900)` | `oklch(0.269 0 0)` (= `secondary`/`accent`/`muted` do v0 — todos compartilham este tom) | renamed |
| `--color-divider` | mix de `#333331` 16% | `oklch(1 0 0 / 10%)` (= `border` do v0) | renamed |
| `--color-status-ok/warn/critical` | `#5e9c76`/`#d98a3d`/`#c24a3f` | **sem mudança** — trilho de status é sinal funcional, não decorativo; spec não pede mudança dele (FR-007: comportamento de navegação/estado permanece) | unchanged |
| `--color-destructive` | não existia | `oklch(0.704 0.191 22.216)` | new |
| `--color-primary-foreground` | não existia (era resolvido via `text-neutral-100` direto) | `oklch(0.205 0 0)` | new |

**Nota sobre `--color-link`**: o v0 não distingue "link" de "muted-foreground" (não há tela com link inline no Assistente). Como o resto do produto usa `text-link` em contexto de texto secundário clicável, reaproveitar o tom `muted-foreground` mantém contraste AA (7.63:1, ver R2) sem inventar uma cor de destaque nova fora do padrão neutro do v0.

**Removidos** (bloco inteiro, não apenas valor): `:root[data-theme="light"]` (`globals.css:80-95`) e toda a lógica que o aciona (`layout.tsx` script anti-FOUC, `theme-toggle.tsx`).

**Sem mudança**: rampas `--color-neutral-*` e `--color-accent-*` (100–900) — nenhum consumidor de `ui/*` referencia essas rampas diretamente fora dos tokens semânticos acima (confirmado por busca: `grep` em `components/ui/*.tsx` não retornou hex nem `oklch` hardcoded). Ficam como estão; podem ser removidas numa limpeza futura se confirmado que nada mais as usa, mas isso é fora do escopo desta rodada (não pedido, não bloqueia nada).
