# Tasks: Normalização de squads exibidas (Squad1–Squad8)

**Input**: Design documents from `/specs/012-normalizar-squads/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: backend tem suíte pytest — migration e comportamento de filtro ganham teste; frontend sem suíte automatizada, validação via `quickstart.md`.

**Organization**: por user story (US1 só squads canônicas, US2 consistência interna) — ambas dependem do backfill, tratado como Foundational.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Foundational — backfill de dado legado (backend)

**Purpose**: corrigir a fonte de verdade (PostgreSQL) antes de qualquer formatação de exibição fazer sentido.

**⚠️ CRITICAL**: bloqueia US1 e US2 — sem o backfill, o dado no banco continua legado.

- [X] T001 Criar `backend/migrations/versions/009_backfill_legacy_squads.py` (`revision = "009"`, `down_revision = "008"`, seguindo o padrão de `008_conversation_archived.py`): `UPDATE workflow_executions SET squad_id = 'SQUAD-01' WHERE squad_id = 'platform'` e equivalentes para `identity`→`SQUAD-02`, `finance`→`SQUAD-03`, `Squad4`→`SQUAD-04` (mapeamento de `data-model.md`), dentro de uma função `upgrade()`; `downgrade()` documentado como no-op justificado (não há como recuperar o nome legado original sem guardar histórico, e voltar pro nome legado não é um estado desejável) — registrar essa decisão em comentário na migration.
- [X] T002 [P] ~~Teste de migration~~ — **desviado**: projeto não tem infraestrutura de teste de Alembic (suíte usa `Base.metadata.create_all`, nunca roda migration real — ver `backend/tests/conftest.py`). Construir isso do zero pra uma migration de backfill único violaria Princípio V (infra que o MVP não usa). Idempotência é garantida estruturalmente por dois mecanismos independentes: (1) Alembic só executa uma revision não aplicada — rodar `upgrade head` de novo é no-op; (2) mesmo se a SQL rodasse de novo, `UPDATE ... WHERE squad_id = '<legado>'` não casa mais nenhuma linha depois da primeira execução. Confirmado empiricamente em T003.
- [X] T003 Rodar `alembic upgrade head` localmente e confirmar via `quickstart.md` Passo 1 (query direta no banco) que não sobra squad legada. Rodado contra o Postgres do `docker compose` (`localhost:5432`, venv local — o container `api` não tem bind mount do código, imagem precisa rebuild separado pra pegar a migration nova). Antes: `Squad4, finance, identity, platform, NULL`. Depois: `SQUAD-01, SQUAD-02, SQUAD-03, SQUAD-04, NULL`. Rodado 2x — segunda vez sem mudança (idempotência confirmada).

**Checkpoint**: banco só tem squads canônicas ou `NULL`.

---

## Phase 2: User Story 1 - Só squads canônicas aparecem na interface (Priority: P1) 🎯 MVP

**Goal**: coluna Squad e filtro mostram só `Squad1`..`Squad8` (ou "—").

**Independent Test**: fila de tickets com execuções antigas (agora com `squad_id` canônico pós-backfill) mostrando `SquadN` formatado; filtro sem duplicata.

- [X] T004 [US1] Em `frontend/src/components/itsm/ticket-table.tsx`, adicionar `SQUAD_LABELS`-like função `formatSquadLabel(squadId: string): string` (`SQUAD-0N` → `SquadN`, valor não reconhecido retorna o próprio valor de entrada — `data-model.md`) e aplicar na célula da coluna Squad (hoje `{item.squad_id ?? "—"}`).
- [X] T005 [US1] Em `frontend/src/components/itsm/ticket-filters.tsx`, mudar `options={[["", "Todas as squads"], ...squads.map((s) => [s, s])]}` para usar `formatSquadLabel(s)` como rótulo, mantendo `s` (valor canônico) como `value` do option — reaproveitou a função de T004 via import de `./ticket-table`.
- [X] T006 [US1] Validar quickstart.md Passos 2 e 3 — confirmado via `curl`/API que `squad_id` só devolve `SQUAD-01..04`/`null` pós-backfill; `formatSquadLabel` mapeia pra `Squad1..Squad4`; `npm run build` compila sem erro de tipo.
- [X] T007 [US1] Validar quickstart.md Passo 3 (round-trip do filtro) — `option.value` continua sendo `s` (canônico), só o `label` muda; querystring `?squad=` inalterada por construção (não tocamos o `value`).

**Checkpoint**: US1 completa e testável isoladamente.

---

## Phase 3: User Story 2 - Consistência entre exibição e roteamento (Priority: P2)

**Goal**: garantir que o pipeline de roteamento nunca mais grava squad fora do conjunto canônico, formalizando o que `normalize_squad` já faz.

**Independent Test**: novo ticket roteado tem `squad_id` gravado e exibido no mesmo squad canônico, sem depender de tradução adicional.

- [X] T008 [P] [US2] Criado `backend/tests/test_squads.py` (11 casos) confirmando `normalize_squad`/`is_known_squad`: variantes canônicas resolvem, nomes legados (`platform`/`identity`/`finance`/`Squad4`/maiúsculo) e `None`/vazio caem em `None`; `SQUADS == (SQUAD-01..08)`. Achado durante o teste: a docstring de `squads.py` linha 27 ("squad 4" e "SQUAD4" resolvem) está desatualizada/incorreta — nenhuma forma sem zero à esquerda resolve hoje; não corrigido por estar fora do escopo desta spec (comentário, não bug funcional).
- [X] T009 [US2] Validado via `ctx_execute` contra a API real: `squad_id` de todos os 200 itens pós-backfill só assume `SQUAD-01..04` ou `null` — nenhum legado.

**Checkpoint**: US1 + US2 completas.

---

## Phase 4: Polish & Cross-Cutting

- [X] T010 [P] `pytest tests/ -k squad` → 44 passed. Suíte completa (`pytest tests/`) também rodada por segurança → **237 passed** (226 prévios + 11 novos de `test_squads.py`), 0 falha, 0 regressão.
- [X] T011 [P] `npm run lint` limpo; `npm run build` compilou com sucesso (Next.js 16, todas as 16 rotas geradas).

## Dependencies & Execution Order

- Phase 1 (T001-T003) bloqueia Phase 2 e Phase 3 — dado precisa estar correto no banco antes de validar exibição.
- T004 e T005 podem ser feitos em sequência (T005 reaproveita a função criada em T004) ou T004 primeiro se extraída pra um módulo compartilhado.
- Phase 3 (US2) é validação/teste de regressão — pode rodar em paralelo com Phase 2 depois que Phase 1 termina, já que não depende do frontend.
- Phase 4 roda por último.

## Parallel Example

```text
# Depois da Foundational:
Task: "T004 [US1] formatSquadLabel em ticket-table.tsx"
Task: "T008 [P] [US2] teste de regressão de roteamento" (arquivo backend diferente, sem dependência de T004)
```

## Implementation Strategy

**MVP**: Foundational (backfill) + US1 já elimina o que o usuário reportou
(nomes legados visíveis). US2 é reforço de regressão para não voltar a
acontecer — baixo custo, vale incluir no mesmo ciclo já que o dado e o
mapeamento já estão prontos.
