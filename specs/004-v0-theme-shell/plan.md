# Implementation Plan: Unificação visual v0 — fundação de tokens + shell

**Branch**: `004-v0-theme-shell` | **Date**: 2026-07-31 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/004-v0-theme-shell/spec.md`

## Summary

Substituir os *valores* dos tokens de cor globais (`--color-*` em `:root`, `frontend/src/app/globals.css`) pela paleta near-black/branco elegante já usada e validada na tela `/assistant` (`.v0-assistant`), mantendo os *nomes* de token existentes — para que todo componente que já consome esses tokens (sidebar, topbar, workspace switcher, e todo `ui/*`: button, card, table, tag, stat, skeleton, empty/error/unavailable-state) herde a paleta nova sem alteração de JSX. Junto: tornar o produto dark-only (remover bloco `:root[data-theme="light"]`, script anti-FOUC, `ThemeToggle` e seu uso na `Topbar`), e adicionar tokens que faltam para cobrir todo caso hoje em uso na tela do Assistente (superfície elevada tipo "card"/"popover", anel de foco, borda de input, cor destrutiva).

## Technical Context

**Language/Version**: TypeScript 5 / Next.js (App Router, React Server + Client Components) — já em uso, sem mudança.

**Primary Dependencies**: Tailwind CSS v4 (`@theme inline`), já em uso. Nenhuma dependência nova.

**Storage**: N/A (mudança é só de CSS/tokens; não toca dado persistido).

**Testing**: `npx tsc --noEmit`, `npx eslint`, mais verificação visual manual no navegador (Chrome, via `mcp__claude-in-chrome`) percorrendo shell + uma tela de ITSM e uma de Agile — consistente com a regra do projeto de testar o caminho real antes de reportar concluído.

**Target Platform**: Web (mesmos browsers já suportados pelo projeto). Sem mudança de plataforma.

**Project Type**: Web application — mudança inteira contida em `frontend/` (o backend não é tocado).

**Performance Goals**: N/A — mudança de valor de token CSS, sem impacto de performance mensurável.

**Constraints**: Contraste AA (4.5:1 texto de corpo, 3:1 texto grande/componente de UI) mantido em toda combinação texto/fundo nova, medido e não estimado (mesma disciplina de `specs/003-unified-ops-refresh/contracts/ui-nav.md`). Zero dependência nova. Zero mudança de nome de token consumido por componente existente (só valor muda, para não gerar diff em `ui/*`).

**Scale/Scope**: 1 arquivo de tokens (`globals.css`), 3 componentes de shell (`sidebar.tsx`, `topbar.tsx`, `workspace-switcher.tsx`), 1 remoção (`theme-toggle.tsx` + sua referência), 1 arquivo de layout raiz (remover script anti-FOUC). ITSM/Agile/`em-construcao` recebem o efeito por herança de token (FR-009), sem edição de arquivo própria nesta rodada.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Princípio V (Simples agora, escalável pelas costuras)**: PASSA. Reaproveita a convenção de nome de token já existente (`--color-*`), reaproveita tokens já existentes (`--color-elevated`, `--color-focus`, `--color-divider`) para os papéis "card/popover", "ring" e "input" em vez de inventar prefixo novo — só `--color-destructive` é token genuinamente novo, porque não existe equivalente semântico hoje. Nenhuma dependência nova. `ThemeToggle` sai da navegação e do disco (não fica código morto).
- Demais princípios (I–IV: determinismo/LLM, entrada não confiável, idempotência, segredo): **N/A** — feature é puramente visual/frontend, sem lógica de negócio, sem chamada externa, sem dado sensível.
- Nenhuma violação a justificar em Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-v0-theme-shell/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output — tokens como entidade
├── quickstart.md        # Phase 1 output — roteiro de validação visual
├── contracts/
│   └── ui-v0-theme.md   # Phase 1 output — contrato de tokens (delta sobre ui-nav.md)
└── tasks.md             # Phase 2 output (/speckit-tasks — not created here)
```

### Source Code (repository root)

```text
frontend/
├── src/
│   ├── app/
│   │   ├── globals.css        # Tokens :root — valores substituídos, bloco [data-theme="light"] removido
│   │   └── layout.tsx          # Script anti-FOUC removido (dark-only, sem tema salvo em localStorage)
│   └── components/
│       └── shell/
│           ├── sidebar.tsx             # Sem mudança de estrutura — herda tokens novos
│           ├── topbar.tsx              # Remove <ThemeToggle />
│           ├── workspace-switcher.tsx  # Sem mudança de estrutura — herda tokens novos
│           └── theme-toggle.tsx        # Removido (arquivo deletado)
```

**Structure Decision**: Mudança contida em `frontend/src/app/globals.css` (fundação) + `frontend/src/components/shell/*` (consumidores diretos do escopo desta rodada). Nenhum diretório novo. `frontend/src/components/ui/*` não é editado — é o teste vivo de que a herança de token funciona sem tocar JSX (FR-004).

## Complexity Tracking

*Sem violação de constituição — seção não se aplica.*
