# Quickstart: validar normalização de squads

## Pré-requisitos

- Stack local rodando (`docker compose up` ou equivalente do projeto) com
  banco de demo populado com execuções antigas contendo squad legada
  (`platform`, `identity`, `finance`, `Squad4`) — ver screenshot que
  originou a spec, tickets `FS-100`, `FS-PROD-1001`, `FS-AUTH-3001`,
  `FS-BILL-2001`.
- Migrations aplicadas (`alembic upgrade head` dentro do container/venv do
  backend), incluindo a nova `009_backfill_legacy_squads`.

## Passo 1 — Confirmar o backfill no banco

```sh
# dentro do container/venv do backend, com DATABASE_URL configurada
psql "$DATABASE_URL" -c "SELECT DISTINCT squad_id FROM workflow_executions ORDER BY squad_id;"
```

**Esperado**: todos os valores retornados pertencem a `SQUAD-01`..`SQUAD-08`
ou são `NULL`. Nenhum `platform`, `identity`, `finance` ou `Squad4` cru.

## Passo 2 — Confirmar a API

```sh
curl -s "http://localhost:8000/api/v1/workflows?limit=200" | jq '[.items[].squad_id] | unique'
```

**Esperado**: mesmo conjunto do passo 1 (`SQUAD-0N` ou `null`).

## Passo 3 — Confirmar a UI

1. Abrir `/itsm` no frontend.
2. Verificar a coluna Squad de cada linha: valores no formato `Squad1`..
   `Squad8` (sem hífen, sem zero à esquerda) ou `—`. Nenhum `platform`,
   `identity`, `finance` ou `Squad4` sem formatação.
3. Abrir o filtro de Squad: a lista de opções mostra `Squad1`..`Squad8`
   (conforme o que existe nos dados), sem duplicata do mesmo squad em dois
   formatos.
4. Selecionar uma squad no filtro e aplicar: a URL fica
   `?squad=SQUAD-0N` (canônico) e a lista filtrada mostra só os tickets
   daquela squad — confirma que o round-trip do filtro não quebrou.

## Passo 4 — Regressão do roteamento

```sh
cd backend && python -m pytest tests/ -k squad
```

**Esperado**: suíte passa sem falha; `normalize_squad` e o roteamento de
novas execuções continuam produzindo `SQUAD-0N`.
