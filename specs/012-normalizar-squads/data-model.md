# Data Model: Normalização de squads exibidas

## Entidades existentes (sem mudança de schema)

### `workflow_executions.squad_id` (coluna existente)

- Tipo: `TEXT`/`VARCHAR`, nullable.
- Hoje contém: valor canônico (`SQUAD-01`..`SQUAD-08`) para execuções
  roteadas depois da introdução de `domain/squads.py`, ou valor legado
  (`platform`, `identity`, `finance`, `Squad4`) para execuções anteriores.
- Depois desta feature: contém exclusivamente valor canônico
  `SQUAD-01`..`SQUAD-08`, ou `NULL`. Nenhuma linha nova é criada — é um
  `UPDATE` sobre linhas existentes.

## Novo conceito de domínio (sem tabela nova)

### Mapeamento legado → canônico

Tabela fechada em código (não em banco), usada tanto pela migration de
backfill quanto por qualquer leitura defensiva futura:

| Valor legado | Squad canônico |
|---------------|-----------------|
| `platform`    | `SQUAD-01`      |
| `identity`    | `SQUAD-02`      |
| `finance`     | `SQUAD-03`      |
| `Squad4`      | `SQUAD-04`      |

*Mapeamento 1:1 arbitrário entre os 4 nomes legados observados e os 4
primeiros squads canônicos — não há informação de negócio que amarre
"platform" a um squad canônico específico (squads.py já documenta que os
squads são genéricos, não a organização real do cliente). Qualquer
atribuição fixa satisfaz o requisito de "não exibir nome legado"; esta é a
mais simples (ordem de aparição na docstring de `squads.py`).*

### Função `formatSquadLabel(squadId: string): string`

- Entrada: valor de `squad_id` já no formato canônico (`SQUAD-0N`) — pós
  backfill, a API sempre devolve esse formato (contrato do endpoint não
  muda).
- Saída: `SquadN` (ex. `SQUAD-04` → `Squad4`). Valor não reconhecido
  retorna o próprio valor de entrada (mesma postura defensiva de
  `PRIORITY_TONE[...] ?? "neutral"` em `ticket-table.tsx`).
- Local: frontend, ao lado das tabelas `STATUS`/`PRIORITY_TONE` já
  existentes em `ticket-table.tsx` (formatação é só apresentação — não há
  necessidade de ida e volta pela API; o valor canônico continua sendo o
  que trafega no filtro/querystring, evitando quebrar o round-trip de
  `?squad=SQUAD-04`).

## Fluxo de dado

```text
[execução histórica]        [execução nova]
squad_id = "platform"       squad_id = normalize_squad(raw) → "SQUAD-0N"
        │                            │
        ▼ (migration 009,            │
           backfill uma vez)         │
squad_id = "SQUAD-01" ──────────────►│
        │                            │
        └──────────────┬─────────────┘
                        ▼
   API devolve squad_id canônico, sem mudança de contrato
                        │
              formatSquadLabel(squad_id)  (frontend, só exibição)
                        ▼
              "Squad1" exibido no frontend
                        │
     filtro/querystring continua usando o valor canônico (SQUAD-01)
```

## Validações

- `display_squad` nunca lança exceção para entrada desconhecida — retorna
  `None` (mesmo tratamento que squad ausente), conforme FR-005 da spec.
- A migration de backfill roda dentro de uma transação e é idempotente
  (rodar duas vezes não altera nada na segunda execução, pois após a
  primeira já não há mais valor legado a atualizar).
