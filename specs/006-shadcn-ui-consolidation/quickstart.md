# Quickstart — validação da rodada 006

**Feature**: `specs/006-shadcn-ui-consolidation`
**Date**: 2026-08-01

Roteiro para provar que a rodada entregou o que a spec pede. Cada bloco tem
**como rodar** e **o que tem que acontecer**. Onde há número, ele é comparável
com a medição de referência tirada antes da correção.

## Pré-requisitos

```bash
cd frontend
npm install          # nenhuma dependência nova deve aparecer no diff
npm run dev          # http://localhost:3000
```

Backend no ar para as telas de ITSM/Agile terem dado; sem ele as telas caem em
estado "indisponível", que também é válido para checar layout mas não para o
quadro.

---

## V1 — Contenção de rolagem (US1, C1)

**Onde**: `http://localhost:3000/agile/kanban` e `/agile/scrum`

Reduza a altura da janela até que a coluna mais cheia não caiba. No console:

```js
const h = document.documentElement;
({ scrollH: h.scrollHeight, clientH: h.clientHeight, delta: h.scrollHeight - h.clientHeight })
```

**Esperado**: `delta === 0`.
**Referência antes da correção**: `scrollH 1905`, `clientH 853`, `delta 1052`.

Confirme também que nenhum posicionado absoluto escapa para o documento:

```js
const vh = document.documentElement.clientHeight;
[...document.querySelectorAll('*')]
  .filter(el => getComputedStyle(el).position === 'absolute'
             && el.getBoundingClientRect().bottom > vh + 2)
  .map(el => el.className)
```

**Esperado**: lista vazia.

Depois, à mão: rolar sobre uma coluna move só aquela coluna; barra lateral,
cabeçalho e abas ficam parados. Repetir em `/agile/scrum` (mesmo componente de
quadro, precisa se comportar igual).

---

## V2 — Revelação sem solavanco (US2, C2)

**Onde**: `http://localhost:3000/assistant`

Abra uma conversa com histórico longo o suficiente para rolar. Antes de enviar,
instale o amostrador:

```js
const vp = document.querySelector('[data-slot="message-scroller-viewport"]');
window.__s = [];
(function tick() {
  window.__s.push({ st: Math.round(vp.scrollTop), sh: vp.scrollHeight });
  window.__raf = requestAnimationFrame(tick);
})();
```

Envie uma pergunta que gere resposta longa. Ao terminar a revelação:

```js
cancelAnimationFrame(window.__raf);
const s = window.__s;
({
  encolheu:  s.some((x, i) => i && x.sh < s[i - 1].sh),   // FR-008 / SC-004
  voltouAoTopo: s.some((x, i) => i && x.st === 0 && s[i - 1].st > 100), // FR-009
})
```

**Esperado**: `encolheu === false` e `voltouAoTopo === false`.
**Referência antes da correção**: ambos `true` — `scrollTop` ia a `0` e
`scrollHeight` caía de `4129` para `3821`.

Ainda nesta tela:

- durante a revelação, nenhum quadro mostra `###`, `**` ou `|` literais (C2.2);
- rolar para cima no meio da revelação não é desfeito pelo sistema (C2.5);
- abrir uma conversa do histórico mostra o conteúdo completo, sem digitação
  (C2.6);
- com movimento reduzido ativo, a resposta aparece inteira de uma vez (C2.7).

Simular movimento reduzido: DevTools → *Rendering* → *Emulate CSS media feature
prefers-reduced-motion: reduce*.

---

## V3 — Tokens saudáveis (C3.8, C3.9)

Em qualquer tela **fora** de `/assistant` (o tema do Assistente é escopado e não
entra nesta rodada), no console:

```js
const p = document.createElement('div');
document.body.appendChild(p);
const read = (c, k) => { p.className = c; return getComputedStyle(p)[k]; };
const out = {
  background: read('bg-background', 'backgroundColor'),
  card:       read('bg-card', 'backgroundColor'),
  muted:      read('bg-muted', 'backgroundColor'),
  accent:     read('bg-accent', 'backgroundColor'),
  border:     read('border border-border', 'borderTopColor'),
  brass500:   read('bg-accent-500', 'backgroundColor'),
  brass800:   read('bg-accent-800', 'backgroundColor'),
};
p.remove(); out
```

**Esperado**:

- nenhum valor `rgba(0, 0, 0, 0)` (hoje `muted`, `card` e `accent` são
  transparentes — token quebrado);
- `background` escuro, não `lab(100 0 0)`;
- `border` discreto, não quase branco;
- `brass500` continua `rgb(201, 162, 39)` e `brass800` continua
  `rgb(92, 74, 18)` — a identidade brass não pode mudar.

Confirme também que a classe morta saiu e que nada depende dela:

```bash
grep -n "^\.dark" src/app/globals.css     # esperado: sem resultado
grep -rn "\btext-muted\b" src/ | wc -l    # esperado: 0 (renomeado)
```

---

## V4 — Controles uniformes (US3, C3)

Percorra `/`, `/itsm`, `/agile`, `/agile/backlog`, `/agile/scrum`,
`/agile/kanban`, `/assistant`.

- Abrir cada campo de seleção: a lista tem o tema do produto, não o widget do
  sistema (C3.1). Os três pontos a checar: seletor de coluna no cartão do
  quadro, filtros de ticket, formulário de ticket.
- Percorrer a tela inteira só com `Tab`: todo controle recebe foco visível, na
  ordem visual (C3.4, C3.5).
- Mover um cartão de coluna **sem mouse**, pelo seletor (C3.7) — este é o
  caminho de acessibilidade do arrastar e soltar e não pode regredir.
- Mover um cartão **com** mouse, para confirmar que o arrastar não quebrou
  (C5.3).

---

## V5 — Entrada de novo chamado (US4, C4)

**Onde**: `http://localhost:3000/itsm`

- A entrada aparece como cartão, sem retângulo sólido claro (C4.1, C4.5).
- Continua sendo link com destino real:

```js
const el = [...document.querySelectorAll('a')].find(a => /Novo chamado/i.test(a.textContent));
({ tag: el.tagName, href: el.getAttribute('href') })
```

**Esperado**: `tag: "A"` e `href: "/itsm/new"`.

- Alcançável por `Tab`, com foco visível, e `Enter` navega (C4.3, C4.4).

---

## V6 — Não regressão (C5)

```bash
cd frontend
npx tsc --noEmit
npx eslint .
git diff --stat package.json package-lock.json
```

**Esperado**:

- `tsc` sem saída;
- `eslint` apenas com o apontamento **pré-existente** de
  `react-hooks/set-state-in-effect` em `src/lib/nav.ts` (`useActiveWorkspace`),
  declarado fora de escopo na spec — nenhum erro novo;
- diff do manifesto vazio (SC-008: nenhuma dependência nova).

Por fim, comparação visual antes/depois de cada tela migrada (SC-007): paleta,
espaçamento e densidade devem estar iguais. A mudança da rodada é de
consistência e de implementação, não de identidade — a única alteração visual
intencional é a entrada de novo chamado (V5).
