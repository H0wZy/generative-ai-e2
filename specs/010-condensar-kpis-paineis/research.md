# Research: Densidade visual dos KPIs e gráficos

## Decisão 1 — Ajustar componentes compartilhados, não cada página

**Decision**: reduzir espaçamento/tamanho em `Stat`, `Card`, `Donut`,
`Burndown` (e `Bars` por consistência), em vez de sobrescrever classes
página a página.

**Rationale**: `Stat` e `Card` já são usados pelas duas telas
(`(shell)/page.tsx` e `(shell)/agile/page.tsx`); um ajuste no componente
garante que FR-004 (consistência entre painéis) seja verdade por
construção, não por disciplina de manter duas implementações
sincronizadas.

**Alternatives considered**: `className` overrides por página — geraria
exatamente o tipo de divergência que a spec quer eliminar (um gráfico de
velocidade "parecendo" diferente entre as duas telas).

## Decisão 2 — Gráficos responsivos em vez de dimensão fixa

**Decision**: `Donut` ganha um tamanho default menor (~104px em vez de
140px) e passa a aceitar ser limitado pelo container via CSS
(`max-width: 100%` no wrapper `<figure>`); `Burndown` reduz a `height`
default (~120px) mantendo `viewBox` proporcional — o SVG já usa
`className="w-full"`, então a largura sempre se ajusta ao container; o
ajuste é a altura base ficar menor para não dominar o cartão.

**Rationale**: o pedido do usuário inclui "grande demais" tanto no
desktop quanto no caso relatado de painel embutido estreito. `Burndown`
já era parcialmente responsivo (`w-full`, `overflow-x-auto`); `Donut`
tinha `size` como número fixo em pixel sem nenhum comportamento
responsivo — reduzir o default e deixar o `<figure>` respeitar a largura
do cartão resolve os dois cenários (SC-002 e SC-003 da spec) sem
reescrever o componente de SVG.

**Alternatives considered**: trocar os gráficos SVG artesanais por uma
biblioteca de charting (Recharts, Visx): resolveria responsividade "de
fábrica", mas é dependência nova e reescrita de 3 componentes para um
problema que é só de tamanho/espaçamento — desproporcional ao pedido,
rejeitado (Princípio V).

## Decisão 3 — Quanto reduzir (metas concretas)

**Decision**: preenchimento de cartão `p-4` (16px) → `p-3` (12px);
`Stat` valor `text-2xl` (24px) → `text-xl` (20px); `Donut` 140px → 104px
(~25% menor, mesma proporção de `SC-001`); `Burndown` altura 160px →
120px (25% menor).

**Rationale**: 25% de redução é o valor mensurável já fixado em SC-001 da
spec para a seção de indicadores — aplicar a mesma proporção aos demais
elementos mantém a redução perceptível e consistente em vez de arbitrária
por componente.

**Alternatives considered**: redução mais agressiva (ex. 40-50%) —
arriscaria FR-005 (legibilidade em zoom 200%, viewport estreito); 25% é o
piso já validado como meta mensurável na própria spec.
