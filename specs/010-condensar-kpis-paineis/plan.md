# Implementation Plan: Densidade visual dos KPIs e gráficos dos painéis

**Branch**: `010-condensar-kpis-paineis` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/010-condensar-kpis-paineis/spec.md`

## Summary

`Stat`, `Card`, `Donut` e `Burndown` usam preenchimento e dimensões fixas
generosas (`Stat`: `p-4` + `text-2xl`; `Donut`: `size=140` fixo em px,
não relativo ao container; `Burndown`: `height=160` fixo). Ajuste é
puramente de tokens de espaçamento/tamanho nesses componentes
compartilhados — como `Stat`, `Card`, `Donut` e `Burndown` já são usados
tanto no painel principal (`/`) quanto no painel Ágil (`/agile`), reduzir
neles garante consistência automática entre as duas telas sem tocar cada
página duas vezes.

## Technical Context

**Language/Version**: TypeScript 5 / Next.js 16, React 19, Tailwind CSS

**Primary Dependencies**: nenhuma nova — só ajuste de classes Tailwind e
props numéricas default nos componentes existentes.

**Storage**: N/A

**Testing**: sem suíte automatizada de frontend; validação visual manual
(`quickstart.md`) em `/` e `/agile` nas larguras descritas na spec (1280px
e ~380px), mais `npm run lint && npm run build`.

**Target Platform**: navegador, incluindo viewport estreito (caso de uso
embutido citado na spec).

**Project Type**: web application (frontend Next.js).

**Performance Goals**: N/A — SVG inline já leve, sem mudança de
complexidade de renderização.

**Constraints**: não pode reduzir contraste/tamanho de fonte abaixo do
legível (WCAG AA já respeitado hoje) nem cortar texto de estado vazio/
indisponível (FR-006 da spec).

**Scale/Scope**: 4 componentes compartilhados
(`ui/stat.tsx`, `ui/card.tsx`, `charts/donut.tsx`, `charts/burndown.tsx`)
+ ajuste de grid nas duas páginas que os consomem (`(shell)/page.tsx`,
`(shell)/agile/page.tsx`); `charts/bars.tsx` também revisado por
consistência (mesmo grid de gráficos).

## Constitution Check

- **V. Simples agora**: mudança é só de tokens de espaçamento/tamanho em
  componentes já compartilhados — reduz necessidade de tocar cada tela
  individualmente (menos código, não mais). PASS.
- Demais princípios não se aplicam (sem LLM, sem dado externo novo, sem
  segredo, sem mudança de persistência).

Nenhuma violação — Complexity Tracking não aplicável.

*Re-check pós Fase 1*: confirmado, escopo ficou ainda mais contido —
nenhuma página nova, só os 4-5 componentes de apresentação.

## Project Structure

### Documentation (this feature)

```text
specs/010-condensar-kpis-paineis/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
└── contracts/
```

### Source Code (repository root)

```text
frontend/src/
├── components/ui/
│   ├── stat.tsx            # p-4→p-3, text-2xl→text-xl, gap/mt reduzidos
│   └── card.tsx             # p-4→p-3, mb-3→mb-2 no CardHeader
├── components/charts/
│   ├── donut.tsx            # size default 140→~104; aceita size responsivo (não só fixo)
│   ├── burndown.tsx         # height default 160→~120
│   └── bars.tsx             # revisão de padding/altura por consistência com os demais
└── app/(shell)/
    ├── page.tsx              # grid gap-3/gap-4 → gap-2/gap-3 onde aplicável
    └── agile/page.tsx        # idem
```

**Structure Decision**: nenhuma página nova; mudança concentrada nos
componentes de apresentação já compartilhados entre os dois painéis, que
é exatamente o que garante a consistência exigida por FR-004 da spec sem
duplicar ajuste em cada tela.

## Complexity Tracking

*Sem violações — não aplicável.*
