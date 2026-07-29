# Contrato — Rotas e shell do frontend

Next.js App Router. Server Components por padrão; cliente só onde há interação.

## Mapa de rotas

| Rota | Workspace | Componente | Dado | Requisitos |
|---|---|---|---|---|
| `/` | compartilhado | Home | `GET /metrics`, `GET /agile/sprint` | FR-010 a FR-013 |
| `/itsm` | ITSM | Fila de tickets | `GET /workflows` com filtros | FR-014 a FR-016 |
| `/itsm/[id]` | ITSM | Detalhe + timeline | `GET /workflows/{id}` | FR-017 a FR-021 |
| `/agile` | Agile | Dashboard de sprint | `GET /agile/sprint` | FR-022 a FR-025 |
| `/agile/backlog` | Agile | Backlog | `GET /agile/backlog` | FR-026 |
| `/agile/scrum` | Agile | Quadro Scrum | `GET /agile/board?scope=sprint` | FR-027 a FR-029 |
| `/agile/kanban` | Agile | Quadro Kanban | `GET /agile/board?scope=board` | FR-027 a FR-029 |
| `/reports` | ambos | Analytics (movido) | rotas `/analytics/*` existentes | FR-032 a FR-035 |
| `/assistant` | ambos | Chat | `POST /assistant/ask` | FR-036 a FR-045 |
| `/em-construcao/[secao]` | ambos | Placeholder nomeado | — | FR-004 |

`/em-construcao/[secao]` cobre Assets, Base de Conhecimento, Automações e Administração com uma única rota dinâmica. Quatro páginas idênticas seriam quatro arquivos para o mesmo conteúdo.

## Shell

`app/layout.tsx` é o shell. Não há route group: todas as rotas usam o mesmo layout, e um group sem segunda variante seria abstração com uma única implementação.

```
┌────────────┬──────────────────────────────────┐
│ marca      │ topbar: seção · tema             │
│ workspace  ├──────────────────────────────────┤
│ [ITSM|Agi] │                                  │
│            │  {children}                      │
│ seções     │                                  │
└────────────┴──────────────────────────────────┘
```

- **Sidebar** — servidor. Seções de `lib/nav.ts` filtradas pelo workspace do `pathname`. Item ativo por `aria-current="page"`.
- **Seletor de workspace** — dois `<Link>` para `/itsm` e `/agile`. Sem estado, sem cliente. É o que satisfaz SC-003: navegação do App Router, não recarga.
- **Alternador de tema** — cliente. Escreve `data-theme` em `<html>` e em `localStorage`.
- **Topbar** — servidor. Título derivado da rota.

### Tema sem piscada

Script inline em `<head>`, antes da pintura:

```js
try {
  const t = localStorage.getItem('theme')
    ?? (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  document.documentElement.dataset.theme = t;
} catch {}
```

Atende FR-005 (preferência do sistema na primeira visita, escolha do usuário depois) sem provider nem hidratação de contexto.

## Componentes de cliente — lista fechada

Todo o resto é servidor.

| Componente | Por quê |
|---|---|
| `shell/theme-toggle` | `localStorage` e evento de clique |
| `itsm/ticket-filters` | Entrada de formulário; escreve em `searchParams` via `router.replace` |
| `itsm/reprocess-button` | Já existe; ação e estado em voo |
| `agile/board` | Drag-and-drop e estado otimista (FR-048) |
| `assistant/chat` | Entrada, histórico de sessão, estado de carregamento |

## Estados obrigatórios por rota

FR-007 e SC-004 exigem carregando, vazio e erro distintos em toda seção. Resolvidos pelas convenções do framework, não por código de estado escrito à mão:

- `loading.tsx` por segmento — esqueleto do conteúdo, não spinner genérico.
- `error.tsx` por segmento — mensagem nomeada e botão de nova tentativa. Falha em `/agile` não derruba o shell (SC-008).
- Vazio é caso do próprio componente: fila sem resultado, backlog vazio, quadro sem sprint, Reports sem base carregada, recorte de filtro sem linha.

**Indisponibilidade não é erro**: `available: false` das rotas de Agile renderiza estado nomeado dentro da página, com a causa e a orientação de configuração. `error.tsx` fica reservado para exceção real.

## Drag-and-drop (FR-029, FR-048)

HTML5 nativo — `draggable`, `onDragStart`, `onDragOver`, `onDrop`. É o que o protótipo já usa. Nenhuma biblioteca.

```
1. onDragStart  → guarda { key, fromColumn }
2. onDrop       → snapshot do estado; move o card localmente (otimista)
3. POST /agile/issues/{key}/transition { target_column }
4. 200          → substitui o status do card pelo new_status_name do Jira
   ≠ 200        → restaura o snapshot; exibe reason e available_transitions
```

**Acessibilidade**: arraste não pode ser o único caminho (FR-008). Cada card tem um menu "Mover para", acionável por teclado, que dispara a mesma requisição.

## Tokens e temas

`globals.css` carrega os tokens Nocturne como custom properties, expostas ao Tailwind v4 por `@theme inline`. Nenhum valor visual literal fora desse arquivo (FR-006, SC-011).

**Divergência consciente do protótipo**, exigida por FR-008: no tema claro, texto secundário e ícone inativo usam `--color-neutral-600` ou mais escuro. O protótipo mantinha `--color-neutral-400` (≈ 2.2:1 sobre branco), que reprova AA. Ver research.md R9.

## Contrato do cliente de API

`lib/api.ts` expõe uma função que nunca lança:

```ts
type ApiResult<T> =
  | { ok: true;  data: T }
  | { ok: false; error: { kind: 'network' | 'http' | 'parse'; status?: number; message: string } }
```

`message` é sempre uma string do próprio frontend, escolhida por `kind` e `status`. Corpo de erro do backend nunca é exibido cru — é o que impede detalhe interno de vazar para a tela.
