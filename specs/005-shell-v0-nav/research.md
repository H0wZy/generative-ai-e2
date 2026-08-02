# Research: Navegação do shell com ícones, colapso e largura estável

## R1 — Diagnóstico ao vivo do bug de largura reportado (US2)

**Decision**: A largura da barra lateral atual (`frontend/src/components/shell/sidebar.tsx`) já é fixa em `md:w-56` (224px) e **não varia** com o conteúdo da área principal — medido ao vivo (não estimado) via `getBoundingClientRect()`/`getComputedStyle()` em três páginas com conteúdos bem diferentes:

| Página | `navWidth` medido | `flex-shrink` computado |
|---|---|---|
| `/itsm` (Dashboard, tabela larga) | 224px | 0 |
| `/agile/backlog` | 224px | 0 |
| `/itsm/new` (formulário) | 224px | 0 |

Não existe nenhuma outra regra de largura para a barra lateral no código hoje (`grep` por `w-56`/`md:w-`/`min-w` em `components/shell` e `app/(shell)` só encontra essa única ocorrência).

**Rationale**: A percepção de "tamanho dinâmico" relatada pelo usuário não tem causa no CSS/componente atual — o candidato mais provável é diferença de largura da *janela do navegador* entre capturas (ex.: DevTools aberto ocupando parte da viewport em um print e não no outro), não uma regra de layout que reage ao conteúdo principal. Ainda assim, o novo componente (R2) tira qualquer dúvida: a largura passa a depender só de um estado local de colapso (dois valores fixos, nunca do conteúdo de `<main>`), o que é uma garantia estrutural mais forte que a atual (largura fixa, mas hoje é só uma classe solta sem nenhum mecanismo que impeça alguém de acoplá-la ao conteúdo no futuro).

**Alternatives considered**: Adicionar teste de regressão visual automatizado (Playwright) para largura da sidebar — rejeitado por escopo: o projeto não tem suíte de testes de frontend hoje (`Testing` = verificação manual/navegador, igual à rodada 004), introduzir uma trilha de testes E2E só para isto seria desproporcional ao problema (que já não se reproduz).

## R2 — Reaproveitar tokens semânticos existentes em vez de expor `v0-*` fora do Assistente

**Decision**: A nova barra lateral do shell usa as classes semânticas **já existentes** (`bg-surface`, `bg-elevated`, `text-text`, `text-muted`, `bg-primary`, `text-primary-foreground`, `border-divider`, `outline-focus`) — as mesmas que `sidebar.tsx`/`workspace-switcher.tsx` já usam desde a rodada 004 — em vez de importar o namespace `v0-*` (`bg-v0-sidebar`, `text-v0-sidebar-foreground` etc.) usado por `components/assistant/conversation-sidebar.tsx`.

**Rationale**: Comparação valor-a-valor em `globals.css` mostra que, desde a rodada 004, os tokens semânticos em `:root` já são **idênticos, oklch a oklch**, aos tokens `v0-*` que a `ConversationSidebar` consome:

| Uso na ConversationSidebar | Token `v0-*` (dentro de `.v0-assistant`) | Token semântico equivalente (`:root`) | Valores |
|---|---|---|---|
| fundo da aside | `bg-v0-sidebar` | `bg-surface` | `oklch(0.205 0 0)` — idêntico |
| texto da aside | `text-v0-sidebar-foreground` | `text-text` | `oklch(0.985 0 0)` — idêntico |
| borda da aside | `border-v0-sidebar-border` | `border-divider` | `oklch(1 0 0 / 10%)` — idêntico |
| hover/ativo de item | `bg-v0-sidebar-accent` | `bg-elevated` | `oklch(0.269 0 0)` — idêntico |
| texto secundário | `text-v0-muted-foreground` | `text-muted` | `oklch(0.708 0 0)` — idêntico |
| ícone/badge ativo, botão novo item | `bg-v0-primary` / `text-v0-primary-foreground` | `bg-primary` / `text-primary-foreground` | `oklch(0.922 0 0)` / `oklch(0.205 0 0)` — idênticos |
| anel de foco / borda de input inline | `v0-ring` | `focus` (usado como `outline-focus`) | `oklch(0.556 0 0)` — idêntico |

Os tokens `--v0-*` só existem dentro do seletor `.v0-assistant` (comentário em `globals.css:148-154` já documenta isso explicitamente: "nunca em `:root`"). Usá-los fora exigiria envolver todo o shell num wrapper `.v0-assistant`, alargando o escopo de uma mudança de navegação para uma mudança de tema (risco maior, viola a estratégia "nomes de token preservados, só valor trocado" já estabelecida na rodada 004). Como os valores já são idênticos, reaproveitar os tokens semânticos entrega o mesmíssimo resultado visual com diff menor e zero tokens novos.

**Alternatives considered**:
- Envolver o shell em `.v0-assistant` e usar `v0-*` diretamente — rejeitado: escopo maior, replica um sistema de cor paralelo sem necessidade, e a decisão "recomendada" do usuário ("clonar padrão v0") é sobre o resultado visual e de interação (ícones, colapso, largura), não sobre qual namespace CSS é usado por baixo — a equivalência de valores garante paridade visual.
- Criar tokens novos `--color-sidebar`/`--color-sidebar-accent` dedicados — rejeitado: os tokens genéricos (`surface`, `elevated`, `muted`) já cobrem o mesmo papel semântico sem introduzir mais um nome para o mesmo valor (YAGNI).

## R3 — Mapa de ícones por item de menu (reaproveitado, não recriado)

**Decision**: Mover o `Record<string, LucideIcon>` hoje definido só em `conversation-sidebar.tsx` (`ICONS`, linhas 38-49) para `frontend/src/lib/nav.ts` (onde `NAV` já vive), exportado como `NAV_ICONS`, e importado tanto por `conversation-sidebar.tsx` quanto pela nova `sidebar.tsx` do shell.

**Rationale**: `NAV` (rótulo → item) já é compartilhado entre os dois componentes; o mapa de ícones é 1:1 com os rótulos de `NAV` e já existe pronto (`lucide-react` já é dependência instalada, usado no Assistente). Duplicar o `Record` nos dois arquivos divergiria silenciosamente se um item de menu mudar de nome no futuro.

**Alternatives considered**: Anexar o ícone diretamente em cada `NavItem` (`icon: LucideIcon` no tipo) — rejeitado por enquanto: exigiria mudar o tipo `NavItem` e todo o array `NAV`, um diff maior que só mover o lookup existente; pode ser feito depois se o mapeamento por string ficar frágil.

## R4 — Colapso: valores e escopo (desktop-only, sem persistência)

**Decision**: Réplica dos valores de largura já usados pela `ConversationSidebar` (280px expandida, 68px colapsada), mas com o controle de colapso visível no breakpoint que o **shell já usa hoje** (`md:`, 768px) em vez do `lg:` (1024px) que a `ConversationSidebar` usa. Estado local (`useState`), sem persistência em `localStorage`/cookie.

**Rationale**: Os valores de largura (280/68px) vêm do Assistente para não haver salto perceptível ao trocar de área. Já o breakpoint de ativação do colapso é mantido no `md:` que o shell já usa para sua própria transição mobile/desktop (FR-004 pede consistência *entre páginas do shell*, não paridade de breakpoint com o Assistente) — introduzir um segundo breakpoint (`lg:`) só para bater com o Assistente criaria uma faixa de largura (768–1024px) em que o shell se comporta diferente de si mesmo hoje, sem nenhum requisito que peça isso. Persistência foi cogitada e descartada: o spec (Edge Cases) já assume estado só de sessão, replicando a regra existente no Assistente — adicionar persistência seria escopo novo não pedido.

**Alternatives considered**: Sincronizar o estado de colapso entre Assistente e shell (um único estado global) — rejeitado: são duas árvores de componente independentes hoje (`ConversationSidebar` dentro de `.v0-assistant`, `Sidebar` do shell fora dela) sem um provider compartilhado; criar um estado global só para isso seria uma abstração nova sem necessidade comprovada (nenhum requisito pede que o colapso persista entre as duas áreas).

## R5 — Comportamento mobile permanece o já existente (faixa horizontal), não o drawer do Assistente

**Decision**: Abaixo do breakpoint `md`, a navegação do shell continua no formato de faixa horizontal rolável (`overflow-x-auto`, sem off-canvas/backdrop) já existente hoje — só ganha ícone ao lado do rótulo em cada item. O padrão de drawer off-canvas com botão hambúrguer e backdrop que a `ConversationSidebar` usa no mobile **não** é replicado.

**Rationale**: O comentário já existente em `sidebar.tsx` (linhas 21-23) documenta uma decisão prévia (FR-009, rodada anterior) contra um drawer: "a 360px uma coluna de 14rem comeria a tela, e um drawer seria mais peça para o mesmo alcance de links". Essa razão continua válida e não foi contestada pelo pedido desta rodada — o pedido do usuário fala em ícones, colapso e largura estável, sempre no contexto de tela larga (colapso é explicitamente "conceito só de desktop" no próprio spec, Edge Cases). Trocar o padrão mobile também seria escopo não pedido e um componente adicional (hambúrguer no topbar + backdrop) sem requisito que o justifique.

**Alternatives considered**: Unificar 100% o comportamento (incluindo mobile) com a `ConversationSidebar` — rejeitado por escopo: nenhuma US ou FR desta rodada menciona o comportamento mobile além de "consistente entre páginas" (FR-004), o que já é verdade hoje e continua sendo com a mudança.
