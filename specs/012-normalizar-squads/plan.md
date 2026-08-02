# Implementation Plan: Normalização de squads exibidas (Squad1–Squad8)

**Branch**: `012-normalizar-squads` | **Date**: 2026-08-02 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/012-normalizar-squads/spec.md`

## Summary

Squads legadas (`platform`, `identity`, `finance`, `Squad4` sem
formatação) gravadas em execuções antigas antes da canonicalização
(`backend/app/domain/squads.py`, SQUAD-01..08) ainda aparecem cruas na
fila de tickets e no filtro de squad. Abordagem: (1) migration Alembic
que faz backfill do `squad_id` legado para o canônico correspondente na
tabela `workflow_executions`, corrigindo o dado na fonte de verdade
(PostgreSQL) — depois disso a API sempre devolve `SQUAD-0N`, contrato
inalterado; (2) uma função de formatação puramente de apresentação no
frontend (`SQUAD-0N` → `SquadN`) usada na coluna Squad e nos rótulos do
filtro, mantendo o valor canônico como o que trafega no querystring
(`?squad=SQUAD-04`), sem quebrar o round-trip de filtro; (3) squad sem
correspondência canônica (residual, se sobrar) cai no estado neutro já
existente ("—"), sem inventar mapeamento.

## Technical Context

**Language/Version**: Python 3.12 (backend, ver `backend/pyproject.toml`), TypeScript 5 / Next.js 16 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic (já em uso em `backend/migrations/`) para o backfill; frontend sem dependência nova — formatação é uma função pura local, mesmo padrão de `PRIORITY_TONE`/`STATUS` em `ticket-table.tsx`

**Storage**: PostgreSQL — única fonte de verdade operacional (constituição, Restrições Técnicas). O backfill altera dado existente, não schema.

**Testing**: pytest (`backend/tests/`) para a migration (roda contra banco de teste) e para a função de formatação; frontend não tem suíte automatizada (`frontend/package.json` só tem `lint`/`build`) — validação de UI é `next lint`, `next build` e verificação manual dos cenários da spec.

**Target Platform**: Linux server (Docker Compose local, alvo Cloud Run futuro)

**Project Type**: web application (backend FastAPI + frontend Next.js)

**Performance Goals**: N/A — mudança é de dado e apresentação, sem novo caminho de leitura/escrita de alto volume.

**Constraints**: migration deve ser idempotente e reversível (padrão já usado em `backend/migrations/versions/00N_*.py`); nenhuma squad real do cliente deve ser inventada — mapeamento cobre exatamente os quatro nomes legados citados na spec (`platform`, `identity`, `finance`, `Squad4`), residual vira "sem squad".

**Scale/Scope**: poucas dezenas de linhas legadas na tabela `workflow_executions` (ambiente de demo/mock); mudança tocando 1 migration, 1 função de domínio, serialização de 2 endpoints (`GET /api/v1/workflows`, `GET /api/v1/workflows/{id}`) e a leitura do valor já formatado em `ticket-table.tsx` / `ticket-filters.tsx`.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Determinismo primeiro**: aplicável por analogia — o mapeamento
  legado→canônico é uma tabela fechada e determinística (sem LLM), squad
  sem correspondência cai em estado neutro em vez de heurística. PASS.
- **II. Entrada externa não confiável**: não se aplica diretamente (squad
  não é texto livre de ticket), mas o mapeamento não interpreta o valor
  legado como instrução, só como chave de lookup. PASS.
- **III. Idempotência e rastreabilidade**: o backfill é uma migration
  idempotente (não duplica execução, não cria dado novo) e preserva
  `workflow_execution_id`/`correlation_id` existentes — só corrige um
  campo. PASS.
- **IV. Segredo nunca entra no repositório**: sem segredo envolvido. PASS.
- **V. Simples agora**: reaproveita `normalize_squad`/`SQUADS` já
  existentes em `domain/squads.py`, sem introduzir tabela de tradução
  paralela nem dependência nova; formatação de exibição é uma função
  pura pequena. PASS.

Nenhuma violação — não há necessidade de Complexity Tracking.

*Re-check pós Fase 1*: o design ficou ainda mais simples que o previsto no
Summary — backend só ganha a migration de backfill, formatação de exibição
é 100% frontend (research.md, Decisão 2). Nenhum gate novo violado.

## Project Structure

### Documentation (this feature)

```text
specs/012-normalizar-squads/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
backend/
├── migrations/versions/
│   └── 009_backfill_legacy_squads.py   # UPDATE workflow_executions SET squad_id = canônico WHERE squad_id IN (legados)
└── tests/
    └── migrations/ (ou equivalente já usado no projeto para migration)  # backfill idempotente, roda 2x sem efeito colateral na 2ª

frontend/
└── src/
    └── components/itsm/
        ├── ticket-table.tsx      # SQUAD_LABELS (SQUAD-0N → SquadN), aplicado só na exibição da coluna Squad
        └── ticket-filters.tsx    # options do filtro de squad usam [valor canônico, rótulo formatado], mesmo padrão de PRIORITY_OPTIONS
```

**Structure Decision**: aplicação web já existente (backend FastAPI +
frontend Next.js, ver `backend/` e `frontend/`). Não há projeto novo. O
backend só precisa da migration de backfill — nenhuma rota, serializer ou
função de domínio nova, porque o valor canônico (`SQUAD-0N`) já é o que a
API devolve hoje para squads roteadas corretamente. A formatação de
exibição (`SquadN`) é responsabilidade só do frontend, mesmo padrão já
usado para status e prioridade em `ticket-table.tsx`/`ticket-filters.tsx` —
evita duas fontes de verdade para o mesmo mapeamento (Princípio V) e não
altera o contrato da API.

## Complexity Tracking

*Sem violações de constituição — seção não aplicável.*
