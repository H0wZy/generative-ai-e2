# Phase 0 — Research: Consolidação de UI em shadcn e correção de scroll/reveal

**Feature**: `specs/006-shadcn-ui-consolidation`
**Date**: 2026-08-01

Todas as descobertas abaixo foram medidas no navegador contra o app rodando em
`localhost:3000`, não inferidas do código. Onde há número, ele veio de execução.

---

## R1 — Por que a página do Kanban rola para fora dos limites

### Investigação

A correção da rodada anterior (`overflow-hidden` no contêiner raiz do shell) não
teve efeito. Medição no `/agile/kanban`, janela de 853px de altura útil:

```
html.scrollHeight = 1905      html.clientHeight = 853
body.scrollHeight = 853
```

O documento rola 1052px além da janela, mas o `body` não. A cadeia de layout
está correta — cada nível está contido:

```
section (coluna)  h=645  clientH=645  scrollH=1764  overflow-y:auto   ← rola dentro de si
div (faixa)       h=653  clientH=653  scrollH=653   overflow-y:hidden
div (página)      h=765  clientH=765  scrollH=765   overflow-hidden
div (layout)      h=808  clientH=808  scrollH=808
main              h=808  clientH=808  scrollH=808   overflow-y:auto
```

Nenhum nível vaza. Ainda assim o documento cresce. O que vaza são 19 elementos
`sr-only` (um por cartão, o rótulo "Mover FRESH-X para" dentro de cada
`<label>`): eles são `position: absolute` e **nenhum ancestral na cadeia é
posicionado**. Logo o bloco contentor deles é o *initial containing block* — o
próprio documento. Elementos posicionados em relação ao ICB não são recortados
por `overflow` de ancestrais estáticos: eles escapam de todos os contêineres e
esticam a área rolável do documento até a posição estática que teriam (y≈1813,
dentro da coluna já rolada).

### Confirmação experimental

A/B no DOM ao vivo, mesma página, mesma janela:

| Intervenção | `html.scrollHeight` |
|---|---|
| estado atual | 1905 |
| `sr-only` → `position: static` | **853** (= janela, exato) |
| restaurado | 1905 |
| `article` → `position: relative` | **853** |

Duas intervenções independentes zeram o vazamento, o que confirma a causa: não é
altura de layout, é bloco contentor.

### Decisão

Duas mudanças, ambas mínimas, uma tratando a causa e outra a classe do defeito:

1. **Remover o `sr-only` de `board.tsx`.** Ele é redundante: o `<select>` irmão
   já tem `aria-label={`Mover ${card.key} para outra coluna`}`, e `aria-label` no
   próprio controle vence o texto do `<label>` no cálculo do nome acessível. O
   span não contribui com nada hoje e é o que quebra o layout. Deletar resolve a
   causa e ainda remove rotulagem duplicada.
2. **Tornar o contêiner de rolagem do shell um bloco contentor** (`position:
   relative` no `<main>`). Isso ancora qualquer descendente absoluto futuro
   dentro da área de conteúdo em vez do documento. Custo: uma classe. Ganho:
   a classe inteira de defeito deixa de ser possível conforme a migração
   introduzir novos `sr-only` (shadcn usa bastante).

### Alternativas consideradas

- **Só adicionar `relative` no cartão**: resolve o sintoma no Kanban, deixa a
  rotulagem duplicada e não protege o resto do produto.
- **Trocar a receita do `.sr-only` global**: toda receita acessível padrão usa
  `position: absolute`; o problema não é a receita, é a falta de ancestral
  posicionado. Mexer no utilitário global afetaria terceiros sem necessidade.
- **`overflow: clip` em algum nível**: não resolve — descendentes cujo bloco
  contentor é o ICB não são recortados por ancestrais estáticos.

### Alcance

Mesmo componente `Board` serve Kanban e Scrum, então uma correção cobre as duas
telas. Os outros dois `sr-only` do projeto (`message-scroller.tsx`,
`breadcrumb.tsx`) ficam dentro de ancestrais posicionados e não vazam; a
mudança (2) os protege de qualquer forma.

---

## R2 — Por que a resposta "dá uma subida" quando começa a digitar

### Investigação

Amostragem quadro a quadro (`requestAnimationFrame`) na conversa com histórico,
do envio da pergunta até o fim da revelação:

```
t=9922   scrollTop=3460  scrollHeight=4129   ← estabilizado
t=22762  scrollTop=0     scrollHeight=3821   ← salta pro topo; conteúdo ENCOLHEU
t=22771  scrollTop=2809  scrollHeight=3449   ← volta
t=22795  scrollTop=2781  scrollHeight=3421
t=23095  scrollTop=2816  scrollHeight=3456   ← daí em diante cresce normal
```

O salto para `scrollTop=0` dura ~9ms e acontece junto de `scrollHeight` caindo
de 4129 para 3821. A ordem importa: **o conteúdo encolhe primeiro**.

Causa: `useTypewriter` inicia com `displayedLength = 0`. No primeiro quadro após
a resposta chegar, `TypewriterMessage` renderiza markdown de string vazia — ou
seja, um bloco de altura ~0. O contêiner de rolagem encolhe, o navegador
*clampa* `scrollTop` para o novo máximo (que naquele instante é menor que a
posição atual), e a conversa visivelmente pula. Quando o texto volta a crescer,
a posição é recalculada — daí o "sobe e volta".

O `scrollToEnd` introduzido na rodada anterior é agravante, não causa: ele
disputa com a âncora da pergunta logo depois do colapso. Some quando a causa é
removida.

### Decisão

**Reservar a altura final do bloco desde o primeiro quadro**, empilhando duas
renderizações do mesmo markdown na mesma célula de grid:

- uma cópia **completa**, invisível e fora da árvore de acessibilidade, que
  define a altura da célula;
- a cópia **revelada**, visível, ocupando a mesma célula.

A célula assume a altura do maior filho — a completa — desde o início. O texto
revelado cresce dentro de espaço já reservado. Consequências diretas:

- `scrollHeight` nunca encolhe (satisfaz SC-004 e FR-008 por construção, não por
  ajuste);
- o markdown continua sendo markdown real durante toda a revelação (FR-007);
- o `scrollToEnd` da rodada anterior é **removido** — sem colapso, o mecanismo de
  âncora do rolador já entrega o comportamento correto (pergunta ancorada no
  topo, resposta crescendo abaixo), que é o de referência.

Reduced motion (FR-012): com `prefers-reduced-motion: reduce`, a revelação é
suprimida e a resposta aparece completa — nesse caso não há cópia dupla.

### Custo e teto conhecido

Renderiza o markdown duas vezes durante a animação (só na mensagem que está
animando, só enquanto anima). Para uma resposta de chat isso é irrelevante. Se
um dia houver streaming real do backend, a cópia completa deixa de existir
(não há "texto final" conhecido) e a abordagem precisa mudar — registrado como
limite, não como dívida silenciosa.

### Alternativas consideradas

- **`min-height` medido via JS**: exige medir fora da tela e sincronizar; mais
  código e um quadro de defasagem. A pilha em grid consegue o mesmo com CSS.
- **Revelar por `clip-path`/máscara sobre o markdown completo**: altura estável
  também, mas revela por linha e não por caractere, e complica seleção de texto.
- **Só remover o `scrollToEnd`**: não resolve — o colapso para altura zero é
  independente dele, como a medição mostra.
- **Não animar**: contraria o pedido explícito.

---

## R3 — A camada de tokens está quebrada para componentes shadcn

### Investigação

Esta é a descoberta que condiciona toda a migração. O `globals.css` mantém
**dois vocabulários** de token:

1. o do projeto (`--color-bg`, `--color-surface`, `--color-elevated`,
   `--color-text`, `--color-muted`, `--color-divider`, `--color-focus`), tema
   escuro, usado pelas telas;
2. o do shadcn (`--background`, `--foreground`, `--card`, `--primary`,
   `--muted`, `--border`, `--ring`, …), declarado em `:root` com valores
   **claros**, e sobrescrito para escuro num bloco `.dark`.

O bloco `.dark` **nunca é aplicado**: o `<html>` não tem a classe.

```
document.documentElement.classList.contains('dark') → false
class="h-full antialiased inter_… font-sans geist_…"
```

Ou seja, as ~32 linhas do bloco `.dark` são CSS morto, e os componentes shadcn
resolvem contra a paleta clara dentro de um app escuro. Valores computados
medidos no navegador:

| Utilitário | Computado hoje | Papel pretendido |
|---|---|---|
| `bg-background` | `lab(100 0 0)` — **branco puro** | fundo escuro do app |
| `border-border` | `lab(90.95…)` — **quase branco** | divisória discreta |
| `bg-primary` | `lab(90.95…)` — quase branco | ação primária |
| `bg-muted` | `rgba(0,0,0,0)` — **transparente** | superfície de hover |
| `bg-card` | `rgba(0,0,0,0)` — **transparente** | superfície de cartão |
| `text-muted` | `lab(66.13…)` | texto secundário (ok) |
| `bg-surface` | `lab(7.78…)` | superfície (ok) |
| `bg-elevated` | `lab(15.20…)` | superfície elevada (ok) |

> **Correção aplicada durante a implementação (2026-08-01).** A tabela acima
> mistura um defeito real com um **artefato da própria medição**. Registrado
> aqui em vez de reescrito, porque a conclusão errada chegou a orientar tarefas.
>
> - **Real**: `bg-background`, `border-border` e `text-foreground` resolviam
>   para valores claros (branco puro, quase branco, quase preto) porque o bloco
>   `.dark` nunca era aplicado. Esses três são usados de verdade em
>   `ui/button.tsx` e `ui/message-scroller.tsx`, então estavam de fato quebrados.
> - **Artefato**: `bg-muted`, `bg-card`, `bg-popover` e `bg-accent` lidos como
>   `transparent` **não estavam quebrados**. A sonda criava um `<div>` e
>   atribuía classes que **não existem no código-fonte**. O Tailwind v4 é JIT:
>   só gera o utilitário se a classe aparecer no fonte escaneado. Nenhum arquivo
>   usa `bg-card`, `bg-popover` ou `bg-muted` "nu" (só `hover:bg-muted`,
>   `aria-expanded:bg-muted`, `bg-muted/50`), então essas classes nunca foram
>   geradas e a sonda leu o fundo padrão de um `div` sem estilo.
> - Consequência: a tese de "ciclo no `@theme inline` invalidando utilitários"
>   **não se sustenta**. O `shadcn/tailwind.css` não declara nenhum `--color-*`
>   (verificado no pacote instalado), logo não havia ciclo com que colidir.
>   Remover as quatro entradas por causa dessa tese quebrou `bg-primary`,
>   `text-primary-foreground` e `text-destructive`, que são usados de verdade —
>   e foram restauradas.
> - Lição para as próximas medições: sondar **elementos renderizados de
>   verdade**, nunca classes sintéticas, quando o motor de CSS é JIT.

Um defeito real, então:

- **Tema invertido**: `bg-background`/`border-border`/`text-foreground` resolvem
  para claro porque o `.dark` não entra — e esses três são efetivamente usados.

Isso explica o incômodo relatado: o "Novo chamado" usa `bg-primary`, que hoje é
quase branco sobre fundo escuro — o retângulo branco reclamado. E explica por que
o `ui/button.tsx` já presente no repositório tem estados que não fazem nada:
seu `hover:bg-muted` é transparente.

### Colisão de vocabulário

Levantamento por nome exato (as contagens ingênuas com `\b` batem no prefixo de
classes escalonadas e inflam o resultado — `bg-accent` casa dentro de
`bg-accent-800`; os números abaixo excluem esse caso):

| Nome | Projeto | shadcn | Colide? |
|---|---|---|---|
| `accent` | **0 usos nus** (só a rampa `accent-100…900`) | superfície de hover | **não** |
| `muted` | `text-muted` = cor de **texto**, 79 usos | `bg-muted` = **superfície**, 6 usos | **sim** |

`accent` não colide: o projeto só usa a rampa numerada, então o nome nu está
livre para o shadcn. Sobra uma única colisão real — `muted` —, e os dois papéis
leem a mesma variável `--color-muted`. Uma variável não pode ser cor de texto e
superfície ao mesmo tempo.

Onde estão os 6 `bg-muted`: **todos dentro de componentes shadcn versionados
pelo projeto** (`ui/button.tsx`, `ui/message-scroller.tsx`). Nenhum em código de
tela. Ou seja, hoje o conflito ainda não machuca o produto — mas machucaria a
cada novo componente adicionado.

### Decisão

**Reconciliar a camada de tokens antes de migrar qualquer componente**, com o
tema escuro como fonte única:

1. Dar aos nomes shadcn os valores escuros do projeto diretamente em `:root`,
   e **remover o bloco `.dark` morto** (nada o aplica; mantê-lo é convite a
   regressão). Mapeamento em `data-model.md`.
2. Remover as entradas auto-referentes do `@theme inline` que invalidam
   utilitários.
3. Resolver a colisão **entregando `muted` ao vocabulário shadcn**: renomear os
   79 `text-muted` do projeto para `text-muted-foreground` e liberar `muted`
   para significar superfície. A troca é mecânica (substituição de token exato,
   verificável por `grep`) e **sem qualquer mudança visual**: hoje `text-muted`
   resolve para `oklch(0.708)` e depois `text-muted-foreground` resolve para o
   mesmo `oklch(0.708)`.

   O caminho oposto — manter `muted` como texto e corrigir à mão os 6 usos
   atuais — tem diff menor agora (6 contra 79), mas é falso barato: cada
   componente shadcn adicionado daqui em diante traz `bg-muted` e precisaria de
   correção manual, indefinidamente. Como o objetivo declarado da rodada é que
   componentes novos entrem sem retrabalho, paga-se a renomeação uma vez.

4. Manter `accent` livre para o shadcn (o projeto não usa o nome nu) e preservar
   intocada a rampa `accent-100…900`, que é a identidade brass do produto.

Isso é pré-requisito de FR-013/FR-014/FR-015: sem ele, todo componente migrado
nasce branco ou transparente, e a identidade visual (FR-015) não se sustenta.

### Alternativas consideradas

- **Aplicar `.dark` no `<html>`**: faria os tokens shadcn ficarem escuros, mas
  deixaria dois vocabulários paralelos vivos e não corrigiria os utilitários
  transparentes (o ciclo no `@theme inline` é independente do tema). Adia o
  problema.
- **Renomear os tokens do projeto para os nomes shadcn**: alinhamento total, mas
  toca ~150 call sites por ganho estético; contraria a Constituição §V
  (mudanças pequenas e reversíveis).
- **Escopar os componentes shadcn sob uma classe própria**, como foi feito com
  `.v0-assistant`: criaria um terceiro vocabulário. O objetivo desta rodada é o
  oposto — convergir.

---

## R4 — Até onde migrar, e o que não trocar

### Inventário medido

Já são shadcn de verdade (base-nova, sobre `@base-ui/react`): `Button`,
`ContextMenu`, `MessageScroller`.

Feitos à mão, com equivalente na biblioteca: `Card`, `Table`, `Skeleton`,
`Tag` (→ Badge).

Sem componente algum hoje, marcação bruta estilizada à mão:

| Controle | Onde |
|---|---|
| `<select>` nativo | `agile/board.tsx`, `itsm/ticket-filters.tsx`, `itsm/ticket-form.tsx` |
| `<input>` / `<textarea>` | `chat-composer.tsx`, `ticket-filters.tsx`, `ticket-form.tsx`, `app-sidebar.tsx`, `reprocess-button.tsx`, `resolve-button.tsx` |
| `<button>` bruto | `app-sidebar.tsx` (5), `chat-composer.tsx` (3), `ai-assistant.tsx` (2), `topbar.tsx`, `source-accordion.tsx`, `empty-state.tsx`, `conversation-view.tsx` |

### Decisão sobre dependências

`@base-ui/react@1.6.0` **já está instalado** e exporta `select`, `scroll-area`,
`input`, `field`, `combobox`, `tabs`, `separator`, `checkbox`, `switch`,
`tooltip`, entre outros. A migração inteira roda com **zero dependência nova**,
atendendo SC-008 e a Constituição §V ("nenhuma dependência nova onde o que já
está instalado resolve").

### Decisão sobre rolagem (confirma A-003)

Não trocar a rolagem nativa por componente de área rolável onde a rolagem
convive com arrastar e soltar — as colunas do quadro. O componente de scroll
area substitui a rolagem nativa por rolagem gerida em script; sobre uma região
de drag-and-drop isso arrisca regressão real (auto-scroll durante arraste,
captura de ponteiro) **sem ganho visual algum**, porque a aparência da barra já
é a mesma pela regra global de `scrollbar` (FR-005, entregue na rodada
anterior). Área rolável entra apenas onde o conteúdo é passivo.

Confirmação de que a aparência já é global e não precisa de componente: a regra
`*` de `scrollbar-width`/`scrollbar-color` no `globals.css` cobre qualquer
região rolável do produto, incluindo as colunas do quadro.

### Decisão sobre "Novo chamado" (confirma A-004)

Vira superfície de cartão clicável, mantendo `<Link>` real (navegação de
verdade, destino no `href`, abre em nova aba com o modificador do sistema,
anunciado como link). Não vira `<button>` com `onClick` de navegação — isso
quebraria semântica e teclado por estética. O contraste sai do preenchimento
sólido e passa para borda + hover, alinhado ao restante do painel.

Nota de UI/UX: a tela mantém uma única ação primária; o cartão continua sendo a
ação de maior destaque da região, só deixa de ser o elemento de maior contraste
da tela inteira.

---

## R5 — Ordem de execução

A ordem é imposta por dependência real, não por preferência:

1. **R3 (tokens)** primeiro — sem isso qualquer componente migrado nasce branco
   ou transparente, e não há como validar FR-015 (identidade preservada).
2. **R1 (sr-only)** e **R2 (typewriter)** em seguida — independentes entre si e
   independentes de (1); são os dois defeitos que o usuário sente hoje.
3. **R4 (migração)** por último, apoiada em (1), telas em fatias verificáveis.

(1) é o único ponto com risco de regressão ampla (mexe em token global), por
isso vem antes e é validado com comparação visual antes/depois em todas as
telas — SC-007.
