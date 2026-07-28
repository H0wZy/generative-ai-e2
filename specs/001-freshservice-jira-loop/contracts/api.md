# Contrato — API exposta

Base: `/api/v1`. Tudo que já existe permanece com o contrato atual; esta
feature acrescenta rotas e dois campos.

## Já existente — preservar

| Rota | Comportamento |
|---|---|
| `POST /tickets/ingest` | Ingestão idempotente. Responde `accepted` ou `duplicate` com `workflow_execution_id` e `internal_correlation_id` |
| `GET /workflows` | Lista execuções com filtro de status. Teto de 200, sem cursor |
| `POST /workflows/{id}/reprocess` | Reprocessa; responde `already_linked` quando o vínculo já existe |
| `GET /metrics` | Contadores por status |
| `GET /health` | Liveness |

### Mudanças aditivas nos contratos existentes

`TicketIngestRequest` ganha um campo opcional:

```
squad: str | None   # valor bruto do campo Squad do Freshservice, até 40 chars
```

Ausente ou vazio: comportamento idêntico ao de hoje (fallback por LLM se
habilitado, senão revisão humana). Nenhum cliente atual quebra.

`WorkflowListItem` ganha:

```
link_origin: "deterministic" | "best_effort" | null
```

`null` enquanto não houver vínculo.

---

## Novo — carga histórica

### `POST /analytics/upload/detect`

Recebe 1 a N arquivos (`multipart/form-data`), classifica cada um pela
assinatura de colunas do cabeçalho, **não grava nada**.

Resposta:

```json
{
  "files": [
    {
      "filename": "Data 20260602.xlsx",
      "kind": "fs_abertos",
      "row_count": 393
    },
    { "filename": "Fechados 20260602.xlsx", "kind": "fs_fechados", "row_count": 2629 },
    { "filename": "jira.csv", "kind": "jira_cards", "row_count": 428 },
    { "filename": "outro.pdf", "kind": "unknown", "row_count": 0 }
  ]
}
```

`kind ∈ {fs_abertos, fs_fechados, jira_cards, unknown, unreadable, too_large}`.

`row_count` é a contagem de linhas **válidas** — o mesmo filtro que o commit
aplica, incluindo o descarte do rodapé de filtros do export. O preview nunca
promete número maior do que o commit grava.

Nome de arquivo não é usado para classificar. Os nomes reais
(`"Data 20260602.xlsx"`) não indicam "aberto" ou "fechado" de forma confiável.

### `POST /analytics/upload/commit`

Recebe os **mesmos** arquivos e grava. Sem estado guardado no servidor entre as
duas chamadas.

```json
{ "inserted": 3050, "updated": 0, "skipped_files": ["outro.pdf"] }
```

Sempre mescla, nunca substitui: upsert por identificador de origem. Recarregar
os mesmos arquivos resulta em `inserted: 0` e todo o resto em `updated`.

Cada arquivo é uma transação: um arquivo que falha não derruba os outros.

### `GET /analytics/data-status`

Estado da base carregada, sem filtro — descreve o que está carregado, não uma
pergunta de negócio.

```json
{
  "hasData": true,
  "chamados": 3022,
  "cards": 428,
  "squads": ["Squad1", "Squad2", "..."],
  "periodo": { "de": "2026-01-05", "ate": "2026-06-02" },
  "ultimaSincronizacao": "2026-07-27T14:02:11-03:00"
}
```

Rota separada dos indicadores de propósito: é o único jeito de decidir "mostrar
carga ou painel" sem depender do sucesso de chamadas que não fazem sentido numa
base vazia.

---

## Novo — indicadores

Todos aceitam o mesmo vocabulário de filtro (11 campos do Freshservice, 6 do
Jira), mais `periodicidade` onde a série temporal faz sentido.

| Rota | Devolve |
|---|---|
| `GET /analytics/filter-options` | Opções de cada campo, com cascata **dentro de cada base** (leave-one-out): escolher `sistema` estreita `tecnologia`; escolher `reporter` não estreita `squad` |
| `GET /analytics/throughput` | Cards concluídos por período. "Concluído" = `Resolution` exatamente `"Done"`. Quebra por squad no formato longo |
| `GET /analytics/distribuicao-trabalho` | Trabalho em execução por responsável e por status. "Em execução" = status em `{QA, In Progress, Deploy, Customer Approved, Code Review}` com responsável atribuído. O gráfico por status devolve **todos** os status, cada um com `ativo: bool` |
| `GET /analytics/lead-time` | Dias entre abertura do chamado e entrega final (último card vinculado em estado terminal). Média **e** mediana — a distribuição tem cauda longa. Campo `amostras` com a contagem do dataset filtrado inteiro |

Filtro de `resolution` aceita o rótulo sintético `"Não resolvido"`, que filtra
`resolution IS NULL` em vez de comparar string — não há como selecionar nulo
num `<select>`.

Indicador que exclui parte da base por falta de vínculo devolve quantos itens
entraram no cálculo (FR-020). Nunca finge cobrir a base inteira.

### `GET /analytics/link-coverage`

O endpoint que prova a feature.

```json
{
  "best_effort": {
    "total_cards": 428,
    "com_vinculo_extraivel": 368,
    "com_chamado_correspondente": 312,
    "cobertura": 0.729
  },
  "deterministic": {
    "total_tombados": 120,
    "com_vinculo": 120,
    "cobertura": 1.0
  }
}
```

---

## Regras que valem para toda a API

- Erro não tratado responde ProblemDetails (RFC 7807), não texto puro.
- Nenhuma resposta contém `requester`, descrição bruta do chamado, saída bruta
  do modelo ou credencial. `WorkflowTicketSummary` continua sendo o filtro.
- Paginação continua sendo `LIMIT` com teto de 200. Cursor permanece fora de
  escopo.
- Nenhuma rota nova dispara efeito externo sem passar pela idempotência
  existente.
