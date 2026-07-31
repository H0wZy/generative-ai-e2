# Quickstart: validar unificação visual v0 (shell)

## Pré-requisitos

- Branch `004-v0-theme-shell` com as mudanças de `globals.css`, `layout.tsx`, `sidebar.tsx`, `topbar.tsx`, `workspace-switcher.tsx` aplicadas, e `theme-toggle.tsx` removido.
- Frontend rodando localmente (`npm run dev` em `frontend/`, ou via `docker compose` conforme o setup do projeto).

## Checks estáticos (rodar antes do check visual)

```bash
cd frontend
npx tsc --noEmit
npx eslint src/components/shell src/app/globals.css src/app/layout.tsx
```

Esperado: zero erro novo introduzido por esta mudança (achados pré-existentes fora do escopo tocado não bloqueiam).

## Validação visual (navegador — Chrome via automação ou manual)

1. Abrir `/assistant` — confirmar que o visual não mudou (referência, não é tocado nesta rodada).
2. Abrir `/` (raiz do shell) ou `/itsm` — confirmar:
   - Fundo quase preto, texto branco elegante na barra lateral e no cabeçalho — mesma paleta do Assistente (SC-001, SC-004).
   - Nenhum "flash" de tema claro no carregamento (recarregar a página algumas vezes) (SC-001).
   - Nenhum botão de alternância de tema claro/escuro no cabeçalho (SC-002).
3. Abrir `/agile` — repetir o mesmo check de barra lateral/cabeçalho.
4. Em qualquer tela de ITSM ou Agile com cartões/tabelas/badges/estado vazio (ex.: lista de tickets), confirmar que esses elementos já aparecem na paleta nova, com texto legível, **sem** ter sido editada nesta rodada (US3, prova de herança de token).
5. Abrir uma tela `em-construcao/[secao]` e confirmar que também reflete a paleta nova.
6. `localStorage`: definir manualmente `localStorage.setItem('theme', 'light')` no console e recarregar — confirmar que **não tem efeito** (produto sempre escuro, SC-001/Edge case).

## Verificação de contraste (medido, não estimado — SC-003)

Usar o DevTools do navegador (aba Accessibility / "Inspect" com contraste exibido, ou a extensão de contraste já usada no projeto) sobre pelo menos:
- Texto de link/label de navegação (`text-muted`, `text-text`) sobre `bg-surface` e `bg-elevated`.
- Texto do botão ativo (`bg-primary`) sobre seu próprio fundo.
- Um estado destrutivo, se houver na tela testada (ex.: badge de erro) — confirmar que segue a regra R2 (nunca texto claro sólido sobre `--color-destructive` cheio).

Confirmar visualmente que todos os pares batem com os números já calculados em `research.md` R2 (todos ≥ 4.5:1 para texto de corpo, exceto o par intencionalmente evitado).

## Critério de conclusão

Todos os itens acima passam **e** nenhuma tela existente (ITSM, Agile, em-construcao) apresenta elemento sem cor definida (transparente/quebrado) — SC-005.
