# Phase 1 Data Model: Localização PT-BR completa do frontend

Esta feature não introduz nem modifica entidade de domínio — é troca de
texto estático de UI e duas correções de bug em componente de apresentação.
Não há schema, tabela ou modelo persistido envolvido.

O artefato mais próximo de um "modelo de dado" é o mapa de tradução dos
rótulos de navegação, que já é o próprio código-fonte (`frontend/src/lib/nav.ts`).
Documentado aqui só como referência de rastreabilidade — não é normativo além
do que o código já expressa:

| Contexto | Antes (EN) | Depois (PT-BR) |
|---|---|---|
| `NAV.itsm[0].label` / `NAV.agile[0].label` | `Home` | `Início` |
| `NAV.itsm[1].label` / `NAV.agile[1].label` | `Dashboard` | `Painel` |
| `NAV.itsm[2].label` | `Assets` | `Ativos` |
| `em-construcao/[secao]/page.tsx` → `SECOES.assets.titulo` | `Assets` | `Ativos` |
| `nav.ts` → `sectionLabel()` fallback | `Home` | `Início` |
| `workspace-switcher.tsx` → `OPTIONS[1].label` | `Agile` | `Ágil` |
| `topbar.tsx` → `WORKSPACE_LABEL.agile` | `Agile` | `Ágil` |
| `app-sidebar.tsx` → logo do shell | `ITSM+Agile` | `ITSM+Ágil` |
| `message-scroller.tsx` → texto `sr-only` (direction=end) | `Scroll to end` | `Ir para o fim da conversa` |
| `message-scroller.tsx` → texto `sr-only` (direction=start) | `Scroll to start` | `Ir para o início da conversa` |
| `agile-tabs.tsx` → `TABS[0].label` | `Dashboard` | `Painel` |
| `app/(shell)/page.tsx` → slice do donut "Volume por status" | `Retry` | `Retry agendado` |
| `not-found.tsx` → link de retorno | `Voltar para a Home` | `Voltar para o início` |

## Estrutura alterada: `NavItem` (`frontend/src/lib/nav.ts`)

Único tipo de dado que muda de forma (não só de valor) nesta feature:

```ts
export type NavItem = {
  label: string;
  href: string;
  implemented: boolean;
  icon: typeof Home; // novo — substitui o lookup NAV_ICONS[label]
};
```

**Antes**: `icon` não existia no tipo; `app-sidebar.tsx` resolvia o ícone em
tempo de render via `NAV_ICONS[item.label] ?? Home`, um `Record<string, Icon>`
paralelo mantido à mão.

**Depois**: cada entrada de `NAV` carrega seu próprio `icon`. Elimina a
possibilidade de um label e sua chave de ícone divergirem (ver research.md D4).

Sem migração de dado — é um tipo de módulo TypeScript, recompilado no build,
sem estado persistido em nenhum storage.
