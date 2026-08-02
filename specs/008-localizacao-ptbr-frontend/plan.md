# Implementation Plan: Localização PT-BR completa do frontend

**Branch**: `008-localizacao-ptbr-frontend` (sem branch dedicada — trabalho aplicado
direto em `main`, ver Complexity Tracking) | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-localizacao-ptbr-frontend/spec.md`

## Summary

Eliminar o inglês residual que sobrava na UI do dashboard (labels de
navegação, seletor de workspace, logo do shell, texto acessível do
Assistente, uma legenda de gráfico) e corrigir dois problemas achados durante
a varredura de código que a acompanhou: uma race condition no board Kanban
(transições concorrentes corrompendo o estado da tela) e o acoplamento
frágil entre o texto do rótulo de navegação e o ícone exibido. Abordagem:
troca direta de string nos componentes existentes — sem biblioteca de
i18n, sem novo estado global, sem mudança de contrato de API.

**Nota de execução**: a tradução e as duas correções de bug já foram
aplicadas durante a sessão que escreveu este plano (auditoria de código
seguida de implementação imediata, dado o baixo risco e escopo contido).
Este documento formaliza a decisão de design para rastreabilidade; `tasks.md`
(gerado por `/speckit-tasks`) referencia esse estado como já concluído.

## Technical Context

**Language/Version**: TypeScript 5, React 19, Next.js 16 (App Router)

**Primary Dependencies**: nenhuma nova. Reaproveita `lucide-react` (ícones),
`@base-ui/react` (Select), Tailwind 4 — todas já presentes em
`frontend/package.json`.

**Storage**: N/A — não há dado persistido; é texto estático em componente.

**Testing**: sem suíte automatizada de frontend no projeto (nenhum
jest/vitest/playwright configurado — `package.json` só tem `lint`). Validação
é `tsc --noEmit`, `eslint`, `next build` e checagem manual das telas
(`/`, `/itsm`, `/agile`, `/ai/chat/[id]`). Mesmo padrão já usado nas rodadas
anteriores (specs 004-007).

**Target Platform**: navegador (Next.js App Router, SSR + client components)

**Project Type**: web application — `frontend/` (Next.js) consumindo API do
`backend/` (fora de escopo desta feature)

**Performance Goals**: N/A — troca de string não afeta orçamento de
performance existente.

**Constraints**: não introduzir biblioteca de i18n (Assumptions do spec);
não alterar rotas nem contratos de API; não quebrar o mapeamento label→ícone
nem a navegação ativa (`mostSpecificMatch`/`sectionLabel`).

**Scale/Scope**: 10 arquivos em `frontend/src` (sidebar, nav, workspace
switcher, topbar, message-scroller, agile-tabs, dashboard, not-found,
em-construção) + 1 arquivo de correção de bug (`board.tsx`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Determinismo primeiro, LLM como fallback medido** — N/A, feature não
  envolve decisão automatizada nem LLM.
- **II. Entrada externa é não confiável** — N/A, todo texto tocado é
  literal estático no código-fonte, não dado de ticket/anexo/terceiro.
- **III. Idempotência e rastreabilidade** — N/A ao texto de UI; a correção
  de race condition em `board.tsx` reforça esse princípio no domínio ágil
  (evita estado incoerente por transição concorrente), então PASSA por
  alinhamento, não por exigência direta.
- **IV. Segredo nunca entra no repositório** — N/A, nenhuma credencial
  envolvida.
- **V. Simples agora, escalável pelas costuras** — PASSA: rejeitada
  deliberadamente a introdução de `next-intl`/biblioteca de i18n para um
  produto com um único idioma-alvo (Assumptions do spec); troca de string
  reaproveita 100% da estrutura existente (`NAV`, componentes shadcn já
  migrados nas rodadas 006/007).

Nenhuma violação — Complexity Tracking fica vazio.

## Project Structure

### Documentation (this feature)

```text
specs/008-localizacao-ptbr-frontend/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md         # Phase 1 output (/speckit-plan command)
├── quickstart.md         # Phase 1 output (/speckit-plan command)
└── tasks.md              # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

Sem `contracts/` — a feature não expõe nem consome interface externa (é
texto estático de UI interno ao `frontend/`); a seção de contratos do
template foi omitida por não se aplicar (regra "Skip if project is purely
internal" do workflow de planejamento).

### Source Code (repository root)

```text
frontend/
└── src/
    ├── lib/
    │   └── nav.ts                          # NAV (labels+ícone por item), sectionLabel()
    ├── components/
    │   ├── shell/
    │   │   ├── app-sidebar.tsx             # consome NAV, logo "ITSM+Ágil"
    │   │   ├── workspace-switcher.tsx      # rótulo "Ágil"
    │   │   └── topbar.tsx                  # WORKSPACE_LABEL
    │   ├── agile/
    │   │   ├── agile-tabs.tsx              # aba "Painel"
    │   │   └── board.tsx                   # fix: race condition em transições concorrentes
    │   └── ui/
    │       └── message-scroller.tsx        # texto sr-only dos botões de rolagem
    └── app/
        ├── (shell)/
        │   ├── page.tsx                    # slice "Retry agendado" no donut de status
        │   └── em-construcao/[secao]/page.tsx  # título "Ativos"
        └── not-found.tsx                   # "Voltar para o início"
```

**Structure Decision**: nenhuma pasta nova. Todas as mudanças ficam dentro de
`frontend/src`, nos mesmos componentes que já possuíam o texto em inglês —
consistente com o principle V (sem infraestrutura que a feature não usa).

## Complexity Tracking

> Fill ONLY if Constitution Check has violations that must be justified

Nenhuma violação — tabela vazia por design.
