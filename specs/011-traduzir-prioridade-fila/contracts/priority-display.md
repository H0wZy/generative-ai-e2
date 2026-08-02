# Contrato: exibição de prioridade

Sem mudança de contrato de API. `GET /api/v1/workflows` e
`GET /api/v1/workflows/{id}` continuam devolvendo `ticket.priority` cru em
inglês (`urgent`/`high`/`medium`/`low`), exatamente como hoje — o contrato
que muda é só a exibição no frontend.

## Antes (bug)

```text
Fila:    Badge mostra "high"
Detalhe: Campo "Prioridade" mostra "high"
Filtro:  já mostrava "Alta" corretamente (única fonte com tradução)
```

## Depois

```text
Fila:    Badge mostra "Alta"       (PRIORITY_LABELS["high"])
Detalhe: Campo mostra "Alta"       (PRIORITY_LABELS["high"])
Filtro:  continua mostrando "Alta" (mesma fonte, agora compartilhada)

Filtro aplicado (?priority=high): sem mudança — valor enviado à API
continua sendo "high", nunca "Alta".
```
