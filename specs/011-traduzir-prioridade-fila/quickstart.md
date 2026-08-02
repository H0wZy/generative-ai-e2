# Quickstart: validar tradução de prioridade

## Pré-requisitos

- Frontend rodando com tickets de prioridades diferentes na fila (urgent,
  high, medium, low).

## Passo 1 — Badge na fila

1. Abrir `/itsm`.
2. Confirmar que o selo de prioridade de cada linha mostra "Urgente",
   "Alta", "Média" ou "Baixa" — nunca o valor em inglês.

## Passo 2 — Detalhe do ticket

1. Abrir o detalhe de um ticket com prioridade "high".
2. Confirmar que o campo "Prioridade" mostra "Alta".

## Passo 3 — Filtro continua funcionando

1. Selecionar "Alta" no filtro de prioridade e aplicar.
2. Confirmar que a URL usa `?priority=high` (valor em inglês) e que a
   lista filtrada mostra só tickets de prioridade alta.

## Passo 4 — Formulário de edição não muda

1. Abrir o formulário de edição de um ticket (via `ticket-edit-panel.tsx`)
   e confirmar que o valor pré-selecionado de prioridade continua correto
   e que salvar não altera o comportamento.

## Passo 5 — Regressão de build

```sh
cd frontend && npm run lint && npm run build
```
