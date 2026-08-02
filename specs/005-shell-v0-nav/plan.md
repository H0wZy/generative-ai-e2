# Implementation Plan: Navegação do shell com ícones, colapso e largura estável

**Branch**: `005-shell-v0-nav` | **Date**: 2026-08-01 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-shell-v0-nav/spec.md`

## Summary

Substituir `frontend/src/components/shell/sidebar.tsx` por uma versão que reproduz o padrão visual/interativo já validado em `components/assistant/conversation-sidebar.tsx` — ícone por item de menu, botão de colapsar/expandir (280px/68px), mesma paleta (reaproveitando tokens semânticos já unificados na rodada 004, sem expor o namespace `v0-*` fora do Assistente) — e ajustar `topbar.tsx` para casar altura/espaçamento com o cabeçalho do Assistente. O bug de largura reportado pelo usuário foi diagnosticado ao vivo (research.md R1): a largura já é fixa hoje (224px, sem variação medida entre páginas); a reescrita reforça essa garantia estruturalmente (largura função só do estado de colapso, nunca do conteúdo de `<main>`).

## Technical Context

**Language/Version**: TypeScript 5 / Next.js (App Router) — mesma stack de specs/002, 003, 004.

**Primary Dependencies**: `lucide-react` (já instalado, usado em `conversation-sidebar.tsx`), Tailwind CSS v4 (`@theme inline` em `globals.css`). Nenhuma dependência nova.

**Storage**: N/A — sem dado persistido; estado de colapso é `useState` local, não persiste.

**Testing**: `tsc --noEmit` + `eslint` (checagens estáticas) + verificação manual em navegador via Chrome (mesmo processo das rodadas 002-004; projeto não tem suíte de teste de frontend hoje — ver research.md R1 para por que uma suíte E2E não é introduzida nesta rodada).

**Target Platform**: Navegador (Next.js dev server, `frontend/` servido via `make frontend`/`npm run dev`, porta 3000).

**Project Type**: Web application (frontend Next.js + backend FastAPI já existente — mudança é 100% frontend).

**Performance Goals**: N/A — mudança de apresentação, sem novo I/O ou chamada de rede.

**Constraints**: Nenhuma cor nova (reaproveita tokens já medidos AA na rodada 004 — research.md R2); nenhum breakpoint novo além do `md:` já usado pelo shell (research.md R4).

**Scale/Scope**: 4 arquivos de componente editados (`sidebar.tsx`, `topbar.tsx`, `workspace-switcher.tsx` ajuste mínimo, `conversation-sidebar.tsx` para importar o mapa de ícones compartilhado) + 1 arquivo de dados (`lib/nav.ts`, novo export `NAV_ICONS`). Sem novas rotas, sem nova página.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constituição do projeto (`.specify/memory/constitution.md`) é focada na trilha Freshservice→Jira/RAG (Princípios I-IV: determinismo/LLM, entrada não confiável, idempotência, segredo) — **N/A** para esta mudança, que é puramente de apresentação no frontend, sem LLM, sem ingestão externa, sem dado persistido, sem segredo.

**Princípio V (Simples agora, escalável pelas costuras)** — **PASS**:
- Nenhuma dependência nova (`lucide-react` já instalado).
- Nenhum token de cor novo — reaproveita os já existentes (research.md R2), evitando um segundo sistema de cor paralelo.
- Nenhuma abstração nova de estado — `useState` local, sem provider/contexto.
- Mapa de ícones consolidado num só lugar (`lib/nav.ts`) em vez de duplicado — reduz superfície, não aumenta.
- Mudança pequena, reversível, testável manualmente (checklist em `quickstart.md`).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
frontend/src/
├── lib/
│   └── nav.ts                          # + export NAV_ICONS (movido de conversation-sidebar.tsx)
├── components/
│   ├── shell/
│   │   ├── sidebar.tsx                 # reescrito: ícones, colapso, largura 280/68px
│   │   ├── topbar.tsx                  # ajuste de padding/altura
│   │   └── workspace-switcher.tsx      # some quando pai está colapsado
│   └── assistant/
│       └── conversation-sidebar.tsx    # passa a importar NAV_ICONS de @/lib/nav
└── app/(shell)/layout.tsx              # sem mudança (continua montando Sidebar/Topbar sem props novas)
```

**Structure Decision**: Web application já existente (`frontend/` Next.js + `backend/` FastAPI, especificado em specs/002/003). Esta rodada não adiciona diretório novo — só edita componentes dentro de `frontend/src/components/shell/` e `frontend/src/lib/nav.ts`, seguindo a mesma estrutura do contrato em `contracts/ui-v0-nav.md`.

## Complexity Tracking

*Sem violação da Constitution Check — seção não aplicável nesta rodada.*
