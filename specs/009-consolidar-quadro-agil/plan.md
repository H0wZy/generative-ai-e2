# Implementation Plan: Quadro Ágil único e drag-and-drop confiável

**Branch**: `009-consolidar-quadro-agil` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-consolidar-quadro-agil/spec.md`

## Summary

Duas rotas (`/agile/scrum`, `/agile/kanban`) renderizam o mesmo componente
`Board`, diferindo só no parâmetro `scope` da API (`sprint` vs `board`) —
consolidar em uma única rota `/agile/quadro` com um toggle de escopo,
mantendo redirect das rotas antigas. O bug de drag-and-drop (arrastar um
card parece "puxar" a barra lateral e outros cards) tem hipótese de causa
raiz concreta: `BoardCard` (`board.tsx`) é `draggable` e contém um
`<Select>` (shadcn/Radix) como filho — o navegador gera a imagem fantasma
do arrasto (`drag image`) automaticamente a partir do snapshot do elemento
arrastado, e conteúdo interativo/portalado aninhado é uma causa conhecida
de drag image corrompida (captura região errada da página). Correção:
definir explicitamente a imagem de arrasto via
`DataTransfer.setDragImage()` com um clone leve só do card, e isolar o
`draggable` do conteúdo interativo do `<Select>`.

## Technical Context

**Language/Version**: TypeScript 5 / Next.js 16 (App Router), React 19

**Primary Dependencies**: já em uso — `@base-ui/react`/shadcn (`Select`),
Tailwind. Nenhuma dependência nova: não introduzir `dnd-kit`/`react-dnd`
para este fix — drag-and-drop nativo (`draggable`, `onDragStart`,
`onDrop`) já funciona corretamente na *lógica* de mover card entre colunas
(`move()` em `board.tsx`); o problema é só a apresentação do drag.

**Storage**: N/A — sem mudança de dado, só de UI e roteamento de tela.

**Testing**: sem suíte automatizada de frontend (`lint`/`build` apenas);
validação por roteiro manual (quickstart.md) em navegador real, já que o
bug é especificamente visual/de renderização do navegador — não
reproduzível por teste de unidade em jsdom.

**Target Platform**: navegador desktop e viewport estreito (caso relatado
de uso embutido em painel lateral).

**Project Type**: web application (frontend Next.js consumindo API já
existente `/api/v1/agile/board`).

**Performance Goals**: N/A.

**Constraints**: não remover o caminho de movimentação por teclado
(`<Select>` "Mover para outra coluna") já existente e acessível — a
correção do drag não pode regredir essa alternativa.

**Scale/Scope**: 1 rota nova + 2 redirects, mudanças em `board.tsx` e
`agile-tabs.tsx`; sem mudança de backend (endpoint `/api/v1/agile/board`
já aceita `scope=sprint|board`).

## Constitution Check

- **V. Simples agora**: consolidar 2 rotas em 1 com toggle é redução de
  superfície, não aumento; drag-image fix é local ao componente existente,
  sem dependência nova. PASS.
- Demais princípios (I-IV) não se aplicam diretamente — feature é só
  frontend, sem LLM, sem dado externo não confiável novo, sem segredo, sem
  mudança de idempotência.

Nenhuma violação — Complexity Tracking não aplicável.

*Re-check pós Fase 1*: confirmado — nenhuma dependência nova, nenhuma
mudança de backend. Design permanece dentro do gate de simplicidade.

## Project Structure

### Documentation (this feature)

```text
specs/009-consolidar-quadro-agil/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

### Source Code (repository root)

```text
frontend/src/
├── app/(shell)/agile/
│   ├── quadro/page.tsx          # NOVO — substitui scrum/page.tsx e kanban/page.tsx, lê ?escopo=sprint|board
│   ├── scrum/page.tsx           # vira redirect (server) pra /agile/quadro?escopo=sprint
│   └── kanban/page.tsx          # vira redirect (server) pra /agile/quadro?escopo=board
├── components/agile/
│   ├── agile-tabs.tsx           # "Quadro Scrum" + "Quadro Kanban" → um único item "Quadro"
│   └── board.tsx                # BoardCard: setDragImage explícito; indicador de drag-over por coluna;
│                                 # toggle de escopo sprint/board dentro da própria tela (client component)
```

**Structure Decision**: mantém a estrutura de rotas App Router já
existente (`app/(shell)/agile/*`); a única rota nova é `quadro`, as duas
antigas viram redirects finos (sem duplicar lógica de fetch/renderização).

## Complexity Tracking

*Sem violações — não aplicável.*
