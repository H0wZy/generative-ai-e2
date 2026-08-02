# Research: Quadro único e drag-and-drop confiável

## Decisão 1 — Consolidar rota (toggle vs. duas rotas)

**Decision**: uma rota `/agile/quadro` com escopo controlado por
querystring (`?escopo=sprint|board`) e um toggle client-side, em vez de
duas páginas.

**Rationale**: `scrum/page.tsx` e `kanban/page.tsx` hoje são idênticas
exceto pelo parâmetro `scope` passado a `apiFetch` e o texto do
cabeçalho — é literalmente o mesmo componente `Board` duas vezes. Uma
única página com toggle elimina a duplicação de código e a confusão de
UX relatada ("parece cópia"), preservando a querystring para permitir
compartilhar/favoritar um link com o escopo específico.

**Alternatives considered**:
- Manter duas rotas, só renomear labels: não resolve a queixa central
  (duas telas visualmente idênticas competindo por atenção na navegação).
- Escopo como aba interna sem refletir na URL: perde a capacidade de
  compartilhar link para um escopo específico — rejeitado.

## Decisão 2 — Causa raiz do bug de drag "vazando" pra sidebar/outros cards

**Decision**: hipótese de trabalho é a imagem de arrasto (drag image)
gerada automaticamente pelo navegador a partir do nó `draggable`
(`<article>` em `BoardCard`), que contém um `<Select>` shadcn/Radix como
filho. Corrigir definindo explicitamente `event.dataTransfer.setDragImage()`
com um elemento clone simples (só o cartão, sem o `Select` embutido) no
`onDragStart`.

**Rationale**: é comportamento documentado do HTML5 Drag and Drop API —
sem `setDragImage` explícito, o navegador tira um "screenshot" do
elemento arrastado no momento do `dragstart` para usar como imagem
fantasma; quando esse elemento contém conteúdo complexo/interativo
(dropdown, portal, elemento com seu próprio stacking context), navegadores
podem renderizar essa captura de forma inconsistente — incluindo, em
alguns casos, capturando/desenhando por cima de outros elementos da
página durante o arrasto, o que bate com o sintoma relatado ("arrasta a
barra lateral e outros cards junto"). Definir a imagem de arrasto
manualmente remove a dependência desse comportamento implícito do
navegador.

**Alternatives considered**:
- Trocar todo o mecanismo por uma biblioteca de drag-and-drop
  (`dnd-kit`/`react-dnd`, drag por ponteiro em vez de HTML5 DnD nativo):
  resolveria de forma mais robusta e testada, mas é dependência nova para
  um problema que tem correção local mais simples — mantido como
  alternativa de escalada caso `setDragImage` não resolva na prática
  (documentado aqui para não perder a opção).
- Aplicar `contain: layout` / `isolation: isolate` no card e nas colunas:
  ajuda a conter *reflow*, mas não resolve o problema de captura de
  imagem de arrasto em si — usado como reforço, não como correção
  principal.

**Nota de risco**: esta é uma hipótese fundamentada em causa conhecida do
HTML5 DnD, não uma causa confirmada por reprodução instrumentada. A tarefa
de implementação deve reproduzir o bug antes de aplicar a correção
(systematic-debugging), e se `setDragImage` não eliminar o sintoma, a
alternativa de biblioteca de drag por ponteiro entra em consideração — sem
isso, não fechar a tarefa como resolvida só por inspeção de código.

## Decisão 3 — Indicador visual de coluna-destino (drag-over)

**Decision**: usar `onDragEnter`/`onDragLeave` por coluna (já existe
`onDragOver` com `preventDefault`) para acrescentar um estado
`isDragOverTarget` por coluna, estilizado de forma distinta do indicador
de WIP estourado já existente.

**Rationale**: reaproveita o mesmo padrão de evento já usado em
`onDrop`/`onDragOver` em `board.tsx`, sem biblioteca nova.

**Alternatives considered**: CSS `:has()` com atributo de estado — mais
frágil de sincronizar com o estado real do arrasto (múltiplos
dragenter/dragleave de elementos filhos disparam falsos positivos); state
React explícito é mais previsível.
