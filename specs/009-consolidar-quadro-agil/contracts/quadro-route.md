# Contrato: rota do Quadro

Sem mudança de contrato de API — `/api/v1/agile/board?scope=sprint|board`
já existe e já é usado pelas duas páginas hoje. O contrato que muda é
só de rota do frontend.

## Rota nova

```text
GET /agile/quadro?escopo=sprint   → equivalente ao antigo /agile/scrum
GET /agile/quadro?escopo=board    → equivalente ao antigo /agile/kanban
GET /agile/quadro                 → default escopo=sprint
```

## Redirects (compatibilidade com links existentes)

```text
GET /agile/scrum   → 307/308 redirect → /agile/quadro?escopo=sprint
GET /agile/kanban  → 307/308 redirect → /agile/quadro?escopo=board
```

## Navegação

`agile-tabs.tsx`: item único `{ label: "Quadro", href: "/agile/quadro" }`
substitui os dois itens atuais (`Quadro Scrum`, `Quadro Kanban`).
