# Quickstart: Navegação do shell com ícones, colapso e largura estável

## Checagens estáticas

```bash
cd frontend
npx tsc --noEmit
npx eslint .
```

## Validação em navegador (Chrome, `npm run dev` na porta 3000)

Pré-requisito: `make dev` ou `cd frontend && npm run dev` rodando.

1. **Ícones (US1, FR-001)** — abrir `/itsm` e `/agile`: cada item de menu (Home, Dashboard, Assets, Base de Conhecimento, Automações, Assistente de IA, Administração, Backlog, Quadro Scrum, Quadro Kanban) mostra um ícone reconhecível ao lado do rótulo, igual ao mapeamento em `data-model.md`.
2. **Colapso (US1, FR-002, FR-005, FR-006)** — em janela larga (≥768px), clicar no botão de colapsar: a barra encolhe para só ícones (68px), rótulos e "em breve" somem, alternador de workspace some, item ativo continua destacado (só o ícone). Clicar em expandir reverte tudo.
3. **Largura estável (US2, FR-003)** — comparar via `document.querySelector('nav[aria-label="Navegação principal"]').getBoundingClientRect().width` (ou inspeção visual) em `/itsm` (Dashboard), `/agile/backlog` e `/itsm/new`: valor idêntico nos três, tanto expandida (280px) quanto colapsada (68px).
4. **Responsivo consistente (US2, FR-004)** — redimensionar a janela cruzando 768px em pelo menos duas páginas do shell diferentes: a transição barra-fixa ↔ faixa-horizontal acontece no mesmo ponto nas duas.
5. **Cabeçalho (US3, FR-007)** — comparar visualmente (screenshot ou régua) a altura/padding/borda do `<header>` do shell com o `<header>` de `/assistant`.
6. **Contraste (FR-008)** — nenhuma cor nova foi introduzida (reaproveita tokens já medidos em specs/004/research.md R2); não precisa remedir, só confirmar visualmente que ícone/texto seguem legíveis nos dois estados (expandido/colapsado) e nos dois workspaces.

## Regressão a não perder

- Link ativo continua destacado (`bg-primary`/`text-primary-foreground`) em qualquer estado.
- Selo "em breve" continua levando para `/em-construcao/[secao]`.
- `ConversationSidebar` do Assistente continua idêntica visualmente após passar a importar `NAV_ICONS` de `@/lib/nav` (mudança é só de onde o mapa vem, não do conteúdo).
