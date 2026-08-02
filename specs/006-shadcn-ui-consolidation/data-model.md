# Phase 1 — Modelo: vocabulário de tokens e inventário de componentes

**Feature**: `specs/006-shadcn-ui-consolidation`
**Date**: 2026-08-01

Esta feature não introduz entidade de dado. O que ela modela é o **vocabulário
de design** — os nomes que a interface usa para se referir a cor, superfície e
raio — e o **inventário de componentes** que consome esse vocabulário. É esse
modelo que a implementação precisa respeitar.

---

## 1. Estado atual (medido, não inferido)

Convivem duas camadas de token no `globals.css`:

| Camada | Prefixo | Tema | Aplicada? |
|---|---|---|---|
| Projeto (ink/brass) | `--color-bg`, `--color-surface`, `--color-elevated`, `--color-text`, `--color-muted`, `--color-divider`, `--color-focus`, `--color-primary` | escuro | sim |
| shadcn (base-nova) | `--background`, `--foreground`, `--card`, `--primary`, `--muted`, `--accent`, `--border`, `--input`, `--ring` | **claro** em `:root`, escuro num bloco `.dark` | **não** — `.dark` nunca entra no `<html>` |
| Assistente (v0) | `--v0-*`, escopado sob `.v0-assistant` | escuro | sim, escopado |

Consequência medida: utilitários shadcn resolvem para claro ou para inválido.

| Utilitário | Computado hoje | Diagnóstico |
|---|---|---|
| `bg-background` | `lab(100 0 0)` | branco puro no app escuro |
| `border-border` | `lab(90.95…)` | borda quase branca |
| `bg-primary` | `lab(90.95…)` | quase branco — o "Novo chamado" |
| `bg-muted` | `rgba(0,0,0,0)` | ⚠️ leitura inválida — ver nota |
| `bg-card` | `rgba(0,0,0,0)` | ⚠️ leitura inválida — ver nota |
| `bg-accent` | `rgba(0,0,0,0)` | ⚠️ leitura inválida — ver nota |
| `bg-surface` | `lab(7.78…)` | correto |
| `bg-elevated` | `lab(15.20…)` | correto |
| `bg-accent-500` | `rgb(201,162,39)` | correto (brass) |
| `bg-accent-800` | `rgb(92,74,18)` | correto |
| `text-muted` | `lab(66.13…)` | correto |

> ⚠️ **Nota de correção (implementação, 2026-08-01)**: as três leituras
> `rgba(0,0,0,0)` são **artefato da sonda**, não token quebrado. O Tailwind v4
> só gera um utilitário se a classe existir no fonte escaneado, e `bg-card`,
> `bg-popover` e `bg-muted` "nu" não aparecem em lugar nenhum do projeto — a
> sonda leu o fundo padrão de um `div` sem estilo. A tese de ciclo no
> `@theme inline` caiu junto: o `shadcn/tailwind.css` não declara nenhum
> `--color-*`. O defeito real era só o tema invertido
> (`bg-background`/`border-border`/`text-foreground`), esse sim em uso.
> Detalhe em `research.md` §R3.

---

## 2. Estado alvo

Uma fonte de verdade: a paleta escura do projeto. Os nomes shadcn passam a ser
**aliases derivados** dela, de modo que qualquer componente adicionado depois
funcione sem edição.

### 2.1 Mapeamento de tokens

| Token shadcn | Valor alvo | Derivado de | Papel |
|---|---|---|---|
| `--background` | `oklch(0.145 0 0)` | `--color-bg` | fundo da aplicação |
| `--foreground` | `oklch(0.985 0 0)` | `--color-text` | texto principal |
| `--card` | `oklch(0.205 0 0)` | `--color-surface` | superfície de cartão |
| `--card-foreground` | `oklch(0.985 0 0)` | `--color-text` | texto sobre cartão |
| `--popover` | `oklch(0.205 0 0)` | `--color-surface` | superfície flutuante |
| `--popover-foreground` | `oklch(0.985 0 0)` | `--color-text` | texto sobre flutuante |
| `--primary` | `oklch(0.922 0 0)` | `--color-primary` | ação primária |
| `--primary-foreground` | `oklch(0.205 0 0)` | `--color-primary-foreground` | texto sobre primária |
| `--secondary` | `oklch(0.269 0 0)` | `--color-elevated` | ação secundária |
| `--secondary-foreground` | `oklch(0.985 0 0)` | `--color-text` | texto sobre secundária |
| `--muted` | `oklch(0.269 0 0)` | `--color-elevated` | **superfície** discreta |
| `--muted-foreground` | `oklch(0.708 0 0)` | valor atual de `--color-muted` | **texto** secundário |
| `--accent` | `oklch(0.269 0 0)` | `--color-elevated` | superfície de hover |
| `--accent-foreground` | `oklch(0.985 0 0)` | `--color-text` | texto sobre hover |
| `--destructive` | `oklch(0.704 0.191 22.216)` | `--color-destructive` | ação destrutiva |
| `--border` | `oklch(1 0 0 / 10%)` | `--color-divider` | divisória |
| `--input` | `oklch(1 0 0 / 15%)` | — | borda de campo |
| `--ring` | `oklch(0.556 0 0)` | `--color-focus` | anel de foco |

### 2.2 Tokens do projeto preservados sem alteração

Continuam existindo e mantêm o significado atual — nenhuma tela precisa mudar
por causa deles:

`--color-bg`, `--color-surface`, `--color-elevated`, `--color-text`,
`--color-divider`, `--color-focus`, `--color-primary`,
`--color-primary-foreground`, `--color-destructive`, `--color-link`,
`--color-status-ok|warn|critical`, rampas `neutral-100…900`,
`accent-100…900`, `accent-2-100…900`, `--space-*`, `--radius-*`, `--shadow-*`.

A rampa `accent-*` é a identidade brass do produto e **não é tocada**. O nome nu
`accent` não é usado pelo projeto em nenhum lugar, então fica livre para o
shadcn sem disputa.

### 2.3 Única renomeação necessária

| De | Para | Ocorrências | Delta visual |
|---|---|---|---|
| `text-muted` | `text-muted-foreground` | 79 | **nenhum** — `oklch(0.708)` antes e depois |

Motivo em `research.md` §R3: libera o nome `muted` para significar superfície,
como todo componente shadcn espera, evitando correção manual perpétua a cada
componente novo.

### 2.4 Remoções

| Item | Motivo |
|---|---|
| bloco `.dark { … }` (~32 linhas) | CSS morto — nada aplica a classe; os valores escuros passam para `:root` |
| entradas auto-referentes do `@theme inline` | formam ciclo e invalidam `bg-muted`, `bg-card`, `bg-accent` |
| `<span class="sr-only">` em `board.tsx` | redundante (o `<select>` já tem `aria-label`) e causa o vazamento de rolagem — `research.md` §R1 |

---

## 3. Inventário de componentes

### 3.1 Já shadcn — só re-verificar após a correção de tokens

`Button`, `ContextMenu`, `MessageScroller`.

### 3.2 Próprios com equivalente na biblioteca — migrar

| Atual | Alvo | Observação |
|---|---|---|
| `ui/card.tsx` | Card | preservar a API `title`/`action` usada pelo painel, ou ajustar chamadas |
| `ui/table.tsx` | Table | — |
| `ui/skeleton.tsx` | Skeleton | — |
| `ui/tag.tsx` | Badge | preservar os 5 tons e os pares de contraste já verificados |

### 3.3 Sem componente hoje — criar a partir da biblioteca

| Controle | Arquivos |
|---|---|
| Select | `agile/board.tsx`, `itsm/ticket-filters.tsx`, `itsm/ticket-form.tsx` |
| Input / Textarea | `assistant/chat-composer.tsx`, `itsm/ticket-filters.tsx`, `itsm/ticket-form.tsx` |
| Button (marcação bruta) | `shell/app-sidebar.tsx` (5), `assistant/chat-composer.tsx` (3), `assistant/ai-assistant.tsx` (2), `shell/topbar.tsx`, `assistant/source-accordion.tsx`, `assistant/empty-state.tsx`, `assistant/conversation-view.tsx` |
| ScrollArea | apenas onde o conteúdo é passivo — **não** nas colunas do quadro |

### 3.4 Permanecem próprios

Sem equivalente direto na biblioteca; passam a se apoiar nas primitivas
migradas, mas não são substituídos: `Stat`, `EmptyState`, `ErrorState`,
`UnavailableState`, `Bars`, `Donut`, `Burndown`, `RankedBars`,
`MessageBubble`, `MarkdownMessage`, `SourceAccordion`, `WorkspaceSwitcher`,
`AppSidebar`, `AgileTabs`.

---

## 4. Invariantes que a implementação deve preservar

- **I-01**: nenhuma cor literal em componente; tudo sai de token.
- **I-02**: nenhum utilitário de cor pode resolver para `transparent` sem
  intenção explícita — é o sintoma de token quebrado.
- **I-03**: os pares texto/fundo mantêm os contrastes já verificados nas rodadas
  004/005; a rampa `accent-*` e os tons de `Tag` não mudam de valor.
- **I-04**: `@base-ui/react` é a única origem de primitiva de UI; nenhuma
  dependência nova (SC-008).
- **I-05**: o tema do Assistente (`--v0-*`, escopado em `.v0-assistant`)
  permanece intocado nesta rodada — foi deliberadamente escopado na spec 003 e
  não faz parte da reconciliação.
