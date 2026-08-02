# Implementation Plan: Tradução da prioridade exibida na fila e no detalhe de ticket

**Branch**: `011-traduzir-prioridade-fila` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/011-traduzir-prioridade-fila/spec.md`

## Summary

`ticket-filters.tsx` já tem a tabela de tradução de prioridade
(`PRIORITY_OPTIONS`), mas ela não é reaproveitada em nenhum outro lugar —
`ticket-table.tsx:65-67` renderiza `item.ticket.priority` cru no badge da
linha, e `itsm/[id]/page.tsx:117` renderiza `detail.ticket.priority` cru no
campo de detalhe. Como o mesmo rótulo é necessário em três lugares (filtro,
badge da lista, campo de detalhe), a correção extrai a tabela para um
módulo compartilhado único em vez de duplicar a tradução pela terceira
vez — evita a mesma classe de bug se um quarto lugar precisar do rótulo no
futuro.

## Technical Context

**Language/Version**: TypeScript 5 / Next.js 16

**Primary Dependencies**: nenhuma nova.

**Storage**: N/A — sem mudança de dado; `item.ticket.priority` continua
sendo o valor original em inglês usado para filtro/ordenação/submissão
(FR-005 da spec), só a exibição muda.

**Testing**: sem suíte automatizada de frontend; validação manual
(`quickstart.md`) + `npm run lint && npm run build`.

**Target Platform**: navegador.

**Project Type**: web application (frontend Next.js).

**Performance Goals**: N/A.

**Constraints**: o valor usado em filtro (`?priority=`), ordenação e
submissão de formulário (`ticket-edit-panel.tsx`) não pode mudar — só a
apresentação ao usuário.

**Scale/Scope**: 1 módulo novo pequeno (`lib/ticket-priority.ts`) + 3
pontos de consumo ajustados (`ticket-filters.tsx`, `ticket-table.tsx`,
`itsm/[id]/page.tsx`).

## Constitution Check

- **V. Simples agora**: extrair para módulo compartilhado só porque agora
  são 3 consumidores (antes só 1) — não é abstração prematura, é remover
  duplicação real assim que ela apareceria pela segunda vez. PASS.
- Demais princípios não se aplicam (sem LLM, sem dado externo novo além do
  já tratado como não confiável, sem segredo, sem mudança de persistência).

Nenhuma violação — Complexity Tracking não aplicável.

*Re-check pós Fase 1*: confirmado — escopo permanece 1 módulo + 3 arquivos
tocados, sem mudança de contrato de API.

## Project Structure

### Documentation (this feature)

```text
specs/011-traduzir-prioridade-fila/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

### Source Code (repository root)

```text
frontend/src/
├── lib/
│   └── ticket-priority.ts       # NOVO — PRIORITY_LABELS (Record<string,string>) + PRIORITY_OPTIONS (pra Select)
└── components/itsm/
    ├── ticket-filters.tsx        # PRIORITY_OPTIONS local → importado de lib/ticket-priority
    └── ticket-table.tsx          # Badge de prioridade usa PRIORITY_LABELS[priority] ?? priority

frontend/src/app/(shell)/itsm/[id]/
└── page.tsx                      # Field "Prioridade" usa PRIORITY_LABELS[detail.ticket.priority] ?? detail.ticket.priority
```

**Structure Decision**: nenhuma rota nova; um módulo `lib/` pequeno
compartilhado pelos 3 pontos que hoje exibem prioridade ao usuário,
seguindo o mesmo diretório onde já vivem outros utilitários de UI
(`lib/nav.ts`, `lib/agile-status.ts`).

## Complexity Tracking

*Sem violações — não aplicável.*
