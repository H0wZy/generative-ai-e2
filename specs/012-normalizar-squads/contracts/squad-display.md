# Contrato: exibição de squad

Não há mudança de contrato de API nesta feature — `GET /api/v1/workflows`
e `GET /api/v1/workflows/{id}` continuam devolvendo `squad_id` no formato
canônico `SQUAD-01`..`SQUAD-08` (ou `null`), exatamente como hoje. O que
muda é puramente a apresentação no frontend.

## Antes (bug)

```text
GET /api/v1/workflows?limit=200
→ items[].squad_id = "platform" | "SQUAD-04" | "identity" | null   (misto, legado + canônico)

Fila de tickets exibe a coluna Squad com o valor cru:
  "platform", "Squad4", "identity", "finance", "—"
```

## Depois (corrigido)

```text
GET /api/v1/workflows?limit=200
→ items[].squad_id = "SQUAD-01" | "SQUAD-04" | null   (sempre canônico, pós-backfill)

Fila de tickets formata para exibição (frontend, sem round-trip pela API):
  formatSquadLabel("SQUAD-01") = "Squad1"
  formatSquadLabel("SQUAD-04") = "Squad4"
  squad ausente                = "—"

Filtro de squad:
  option.value = "SQUAD-01"          (o que vai no querystring ?squad=)
  option.label = "Squad1"            (o que o usuário vê)

GET /api/v1/workflows?squad=SQUAD-01
→ continua comparando direto contra a coluna squad_id no banco, sem mudança
```

## Garantias

- Nenhum endpoint muda formato de resposta.
- Nenhum client existente que já lida com `SQUAD-0N` quebra.
- O filtro por squad continua funcionando via comparação exata de string no
  backend (`WorkflowExecutionRow.squad_id == squad`), porque o valor
  enviado pelo frontend no querystring continua sendo o canônico.
