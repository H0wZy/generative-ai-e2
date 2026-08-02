# Contrato: props dos componentes de KPI/gráfico

Sem mudança de contrato de API. O "contrato" aqui é a assinatura pública
dos componentes React reaproveitados pelas duas telas — precisa
permanecer compatível com todos os chamadores existentes.

```ts
// Donut — size continua opcional, só o default muda
function Donut(props: { slices: Slice[]; label: string; size?: number }): JSX.Element
// antes: size = 140
// depois: size = 104

// Burndown — height continua opcional, só o default muda
function Burndown(props: { series: BurndownSeries; height?: number }): JSX.Element
// antes: height = 160
// depois: height = 120

// Stat e Card — sem mudança de props, só de classes internas
function Stat(props: { label: string; value: ReactNode; hint?: ReactNode }): JSX.Element
function Card(props: { title?: ReactNode; action?: ReactNode; children: ReactNode; className?: string }): JSX.Element
```

Nenhum chamador (`(shell)/page.tsx`, `(shell)/agile/page.tsx`) precisa
mudar a forma como invoca esses componentes — todos herdam o novo
tamanho por default.
