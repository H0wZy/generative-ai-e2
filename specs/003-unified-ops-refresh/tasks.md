# Tasks: Refresh Operacional — Ticket ao Vivo, Assistente Persistente, Identidade Visual

**Input**: Design documents from `specs/003-unified-ops-refresh/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: incluídos — o backend deste projeto tem 100% de cobertura por convenção já estabelecida (24 arquivos em `backend/tests/`, Postgres real, sem mock de banco). Frontend não tem suíte automatizada hoje (plan.md, Technical Context); validação de UI é manual via `quickstart.md`, não fabricada aqui.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: US1 (P1) · US2 (P2) · US3 (P3) · US4 (P4) — tarefas de Setup/Foundational/Infra/Polish não têm rótulo

---

## Phase 1: Setup

- [X] T001 Adicionar serviço `worker` (`python -m app.worker --loop`) ao `docker-compose.yml`, mesma imagem do serviço `api`, `depends_on: postgres` (research.md R1 — sem isso nada drena `retry_scheduled` fora do gatilho manual)

---

## Phase 2: Foundational (Blocking Prerequisites)

**⚠️ CRITICAL**: bloqueia US1, US3 e US4 — todas tocam as tabelas abaixo.

- [X] T002 Adicionar `resolved_at: Mapped[datetime | None]` em `TicketRow`, e os modelos ORM `AssistantConversationRow` (`session_id` PK) e `AssistantMessageRow` (`id` PK, `conversation_id` FK, `role`, `text`, `sources_json`, `created_at`, índice em `(conversation_id, created_at)`) em `backend/app/repositories/schema.py` (data-model.md §1–3)
- [X] T003 Criar migration Alembic `backend/migrations/versions/004_ticket_resolution_and_conversations.py`: `ALTER TABLE tickets ADD COLUMN resolved_at TIMESTAMPTZ NULL`, `CREATE TABLE assistant_conversations`, `CREATE TABLE assistant_messages` com índice — depende de T002
- [X] T004 Adicionar `assistant_messages` e `assistant_conversations` (nessa ordem, FK primeiro) à lista `_TABLES` de truncamento em `backend/tests/conftest.py` — depende de T002

**Checkpoint**: `make migrate` roda limpo, suíte de testes ainda verde antes de qualquer código novo.

---

## Phase 3: User Story 1 — Criar e acompanhar um chamado que vira issue real no Jira (Priority: P1) 🎯 MVP

**Goal**: tela cria chamado, reaproveita `/tickets/ingest` + `/workflows/process-next` já existentes, issue aparece no Jira em segundos; edição e "marcar concluído" ficam disponíveis no detalhe.

**Independent Test**: abrir `/itsm/new`, criar um chamado, ver a issue aparecer na lista em poucos segundos com a chave do Jira (quickstart.md §2).

### Tests for User Story 1

- [X] T005 [P] [US1] Teste de contrato para `PATCH /workflows/{id}/ticket` (edição válida, 404, 409 quando `resolved_at` preenchido) em `backend/tests/test_ticket_edit.py`
- [X] T006 [P] [US1] Teste de idempotência para `POST /workflows/{id}/resolve` (duas chamadas devolvem o mesmo `resolved_at`, sem erro) em `backend/tests/test_ticket_resolve.py`

### Implementation for User Story 1

- [X] T007 [US1] Adicionar `resolved_at: datetime | None` a `WorkflowListItem` e `WorkflowDetail` em `backend/app/domain/models.py` — depende de T002
- [X] T008 [US1] Adicionar `update_ticket_fields(workflow_execution_id, **fields) -> WorkflowDetail | None` (409 se já resolvido) e `mark_resolved(workflow_execution_id) -> datetime` (idempotente) em `WorkflowRepository`, `backend/app/repositories/workflows.py` — depende de T007
- [X] T009 [US1] Incluir `resolved_at` no `SELECT` de `list_workflows()` e `get_workflow_detail()` em `backend/app/repositories/workflows.py` — depende de T007
- [X] T010 [US1] Adicionar rotas `PATCH /workflows/{workflow_execution_id}/ticket` e `POST /workflows/{workflow_execution_id}/resolve` em `backend/app/api/routes.py` (contracts/api-tickets.md) — depende de T008
- [X] T011 [P] [US1] Criar `frontend/src/components/itsm/ticket-form.tsx` (assunto, descrição, prioridade, categoria — reusado para criar e editar)
- [X] T012 [P] [US1] Criar `frontend/src/components/itsm/resolve-button.tsx` (chama `POST .../resolve`, desabilita durante a requisição)
- [X] T013 [US1] Criar `frontend/src/app/itsm/new/page.tsx`: usa `ticket-form.tsx`, gera `event_id` via `crypto.randomUUID()`, chama `POST /tickets/ingest` seguido de `POST /workflows/process-next`, redireciona para o detalhe (contracts/api-tickets.md §Fluxo) — depende de T011
- [X] T014 [US1] Adicionar formulário de edição (`ticket-form.tsx`) e `resolve-button.tsx` a `frontend/src/app/itsm/[id]/page.tsx`, chamando `PATCH .../ticket` — depende de T010, T012
- [X] T015 [US1] Adicionar link "Novo chamado" na fila em `frontend/src/app/itsm/page.tsx` apontando para `/itsm/new`

**Checkpoint**: US1 completa e testável isoladamente (quickstart.md §2).

---

## Phase 4: User Story 2 — Identidade visual única e navegação sem ambiguidade (Priority: P2)

**Goal**: paleta/tipografia/trilho de status únicos em toda tela; sidebar nunca troca de workspace sozinha; Reports sai da navegação e do disco.

**Independent Test**: navegar por todas as telas e comparar visualmente; clicar em item compartilhado a partir de `/agile/*` e confirmar que o workspace não muda (quickstart.md §3).

- [X] T016 [P] [US2] Substituir os tokens de cor em `frontend/src/app/globals.css` (`:root` e `:root[data-theme="light"]`) pelos valores novos — contracts/ui-nav.md §tokens
- [X] T017 [P] [US2] Remover o item `Reports` dos arrays `itsm` e `agile` em `frontend/src/lib/nav.ts`
- [X] T018 [US2] Corrigir preservação de workspace: mover a decisão de "workspace ativo" para estado local do `Sidebar` (`frontend/src/components/shell/sidebar.tsx`) em vez de recalcular via `workspaceFor()` para toda rota — depende de T017
- [X] T019 [P] [US2] Aplicar trilho de status (borda esquerda 3px, cor do `tone` já resolvido por `Tag`) em `frontend/src/components/itsm/ticket-table.tsx`
- [X] T020 [P] [US2] Aplicar o mesmo trilho de status aos cards em `frontend/src/components/agile/board.tsx` (compartilhado por Kanban e Scrum) e `frontend/src/components/agile/backlog-table.tsx`
- [X] T021 [US2] Remover `frontend/src/app/reports/` por completo (`page.tsx`, `actions.ts`, `fields.ts`, `filter-bar.tsx`, `upload-screen.tsx`, `error.tsx`, `loading.tsx`) — depende de T017
- [X] T022 [US2] Remover rotas `/analytics/*` de `backend/app/api/routes.py`, o módulo `backend/app/services/analytics/`, os testes `backend/tests/test_analytics_*.py` e as fixtures de `examples/` que só eles consomem (grep antes de apagar cada fixture) — depende de T021

**Checkpoint**: US2 completa e testável isoladamente (quickstart.md §3). `/reports` devolve 404.

---

## Phase 5: User Story 3 — Conversa com o assistente sobrevive à navegação (Priority: P3)

**Goal**: histórico de conversa persistido por sessão sem login, isolado por visitante.

**Independent Test**: perguntar, navegar, voltar — conversa intacta; fechar/reabrir o navegador — conversa intacta; sessão diferente — conversa vazia (quickstart.md §4).

### Tests for User Story 3

- [X] T023 [P] [US3] Teste de persistência e isolamento: duas sessões (`X-Session-Id` diferentes) nunca leem a conversa uma da outra; `GET /assistant/conversation` sem histórico devolve `{"messages": []}`, não 404 — em `backend/tests/test_assistant_conversation.py`

### Implementation for User Story 3

- [X] T024 [US3] Criar `AssistantConversationRepository` em `backend/app/repositories/assistant.py` (novo arquivo, mesmo padrão de `workflows.py`): `get_or_create(session_id)`, `append_message(session_id, role, text, sources_json)`, `list_messages(session_id)` — depende de T002
- [X] T025 [US3] Adicionar `GET /assistant/conversation` (lê header `X-Session-Id`) e persistir pergunta+resposta em `POST /assistant/ask` (sem o header, degrada para não persistir — nunca falha) em `backend/app/api/routes_assistant.py` — depende de T024
- [X] T026 [P] [US3] Criar `frontend/src/lib/session.ts`: gera/lê um `crypto.randomUUID()` em `localStorage`, expõe helper para anexar `X-Session-Id` nas chamadas do assistente
- [X] T027 [US3] Atualizar `frontend/src/components/assistant/chat.tsx` para carregar histórico via `GET /assistant/conversation` no mount e enviar o header em todo `POST /assistant/ask` — depende de T025, T026

**Checkpoint**: US3 completa e testável isoladamente (quickstart.md §4).

---

## Phase 6: User Story 4 — Assistente responde sobre um chamado específico e formata a resposta (Priority: P4)

**Goal**: pergunta citando uma chave Jira traz dado real como contexto best-effort; resposta renderiza negrito/itálico/link de verdade.

**Independent Test**: perguntar pela chave de um chamado existente e por uma inexistente; perguntar "onde vejo o backlog" e conferir o link clicável (quickstart.md §5).

### Tests for User Story 4

- [X] T028 [P] [US4] Teste da heurística de chave Jira: chave existente preenche `ticket_context`, chave inexistente devolve `ticket_context: null` sem erro, pergunta sem chave nunca consulta o banco — em `backend/tests/test_assistant_ticket_context.py`

### Implementation for User Story 4

- [X] T029 [US4] Adicionar `TicketRefSource` (`jira_issue_key`, `status`, `subject`, `squad_id`) e o campo `ticket_context: TicketRefSource | None = None` em `AssistantAnswer`, `backend/app/domain/assistant.py` (data-model.md §4)
- [X] T030 [US4] Adicionar `find_by_jira_key(jira_issue_key) -> WorkflowDetail | None` em `WorkflowRepository`, `backend/app/repositories/workflows.py`
- [X] T031 [US4] Adicionar regex de chave Jira (`[A-Z][A-Z0-9]*-\d+`) e a busca best-effort (falha do banco não bloqueia) em `ask()`, estendendo `_wrap()` para aceitar origem `"ticket:{key}"`, em `backend/app/services/assistant.py` — depende de T029, T030
- [X] T032 [US4] Atualizar `_SYSTEM_PROMPT` em `backend/app/services/assistant.py` com instrução de negrito/itálico (`**`/`*`) e link de navegação só como `[texto](/rota)` de uma lista fechada de rotas reais (contracts/api-assistant.md)
- [X] T033 [US4] Passar `ticket_context` do resultado de `ask()` para a resposta HTTP em `backend/app/api/routes_assistant.py` — depende de T031
- [X] T034 [P] [US4] Criar `frontend/src/lib/markdown.ts`: parser mínimo para `**negrito**`, `*itálico*`, `[texto](href)`; `href` só vira link clicável se estiver na allow-list derivada de `NAV` (itens `implemented: true`) — research.md R5
- [X] T035 [US4] Atualizar `frontend/src/components/assistant/message.tsx` para renderizar `answer` via `markdown.ts` (em vez de `whitespace-pre-wrap` cru) e mostrar `ticket_context` (quando presente) como bloco de fonte, texto simples — depende de T034, T033

**Checkpoint**: US4 completa e testável isoladamente (quickstart.md §5). Todas as 4 user stories funcionam juntas.

---

## Phase 7: Infraestrutura — Unificação do provedor de LLM (cross-cutting, fora das 4 User Stories)

Não pertence a nenhuma User Story do spec.md — vive só em Assumptions e no Complexity Tracking do plan.md, como exceção de Constituição.

- [X] T036 Criar `OpenRouterSquadClient` em `backend/app/integrations/llm.py`, implementando `LLMClientProtocol`, delegando a chamada HTTP para `OpenRouterClient.complete()` (`backend/app/integrations/openrouter.py`) com prompt de JSON estrito, `json.loads()` do mesmo jeito que `OllamaClient` já faz (research.md R2)
- [X] T037 Atualizar defaults de `llm_base_url`/`llm_model` para o provedor/modelo OpenRouter em `backend/app/core/config.py` — depende de T036
- [X] T038 Trocar `OllamaClient` por `OpenRouterSquadClient` em `_augment_with_llm()`, `backend/app/services/processing.py` — depende de T036
- [X] T039 Rodar `make routing-eval` contra o novo provedor e registrar ADR-013 em `docs/ai/ai-decisions.md` com o número real (Princípio I — golden set decide, não confirma) — depende de T038, **bloqueia `LLM_ENABLED=true` virar padrão**. Corrigido `backend/scripts/routing_eval.py` para importar `OpenRouterSquadClient` em vez de `OllamaClient`; `.env` local corrigido para `LLM_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free` (estava com o valor antigo do Ollama). Medido: accuracy=83.33% (10/12), injection_attack_success_rate=33.33% (1/3) — ADR-013 registrada. `LLM_ENABLED=false` permanece o padrão.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T040 [P] Atualizar a seção "o que ficou de fora" do `README.md` (Reports removido, provedor de LLM unificado, limitação de concorrência de `process-next` — research.md R1)
- [X] T041 [P] Registrar evidência desta feature em `evidence/evaluations/` e atualizar `docs/ai/ai-decisions.md` (evidence-scribe, Fluxo de Trabalho da Constituição passo 5). Registrado em `evidence/evaluations/2026-07-30-spec-003-unified-ops-refresh.md`, commit f195953. Sem issue GitHub dedicada a fechar (verificado).
- [X] T042 Revisão `cybersec`: cobertura de `redaction.py` no novo caminho de contexto de ticket, confiança depositada em `X-Session-Id` sem assinatura (mesmo nível de confiança já aceito no resto do app, mas documentar explicitamente). Achado real: `ticket_context.subject` só era redigido ao montar o prompt, não no objeto devolvido/persistido — corrigido em `services/assistant.py::_find_ticket_context`. Documentado em ADR-012 (docs/ai/ai-decisions.md).
- [X] T043 Rodar `quickstart.md` do início ao fim (qa-dev, evidência de execução real — Fluxo de Trabalho passo 4, não revisão de código). 5/6 seções PASS via API/DB direto (204/204 testes, migration, US1/US3/US4, golden set remedido — 2ª rodada registrada em ADR-013). US2 (visual/nav) precisa de navegador, não verificável via API — sinalizado, não bloqueante.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependências
- **Foundational (Phase 2)**: bloqueia US1 (T007+), US3 (T024+) e US4 (T029 usa o mesmo `schema.py`, ainda que a tabela em si seja de US1/US3) — nenhuma User Story começa antes de T002–T004
- **US1–US4 (Phases 3–6)**: cada uma parte da Foundational; entre si, só compartilham arquivos de UI shell (`nav.ts`, `globals.css` em US2) — de resto, independentes
- **Infra LLM (Phase 7)**: independente de todas as 4 User Stories, pode rodar em paralelo com qualquer uma delas
- **Polish (Phase 8)**: depende de todas as fases anteriores estarem concluídas

### User Story Dependencies

- **US1 (P1)**: depende só da Foundational — nenhuma dependência de US2/US3/US4
- **US2 (P2)**: depende só da Foundational — toca arquivos de shell (`nav.ts`, `globals.css`) que US1/US3/US4 não editam
- **US3 (P3)**: depende só da Foundational — sem relação de código com US1/US2/US4
- **US4 (P4)**: depende só da Foundational; reaproveita `WorkflowRepository` (US1) só como leitura — nenhuma escrita concorrente com US1

### Parallel Opportunities

- Dentro da Foundational: nenhuma — T002→T003→T004 é uma cadeia sobre o mesmo arquivo/schema
- **US1, US2, US3, US4 podem ser implementadas em paralelo por agentes/devs diferentes assim que a Foundational fechar** — é a divisão natural para os sub-agentes que o usuário autorizou
- Dentro de cada story, tarefas `[P]` (arquivos distintos, sem dependência pendente) — ver marcação em cada tarefa acima
- Fase 7 (LLM) é paralela a qualquer uma das 4 stories

---

## Parallel Example: rodando as 4 User Stories em paralelo

```text
Depois de T001–T004 (Setup + Foundational) fechados:

Agent A → Phase 3 (US1): T005–T015
Agent B → Phase 4 (US2): T016–T022
Agent C → Phase 5 (US3): T023–T027
Agent D → Phase 6 (US4): T028–T035
Agent E → Phase 7 (Infra LLM): T036–T039
```

US4 (T031) só *lê* `WorkflowRepository`, adicionando um método novo (`find_by_jira_key`) sem tocar nos métodos que US1 está escrevendo (`update_ticket_fields`, `mark_resolved`) — colisão de arquivo (`workflows.py`), não de lógica; sequenciar essas duas edições ou revisar o merge é o único ponto de atenção real entre stories.

---

## Implementation Strategy

### MVP First (User Story 1 apenas)

1. Phase 1 (Setup) + Phase 2 (Foundational)
2. Phase 3 (US1) completa
3. **PARE e VALIDE**: quickstart.md §2 isoladamente
4. Já é demonstrável: chamado criado na tela vira issue real no Jira em segundos

### Entrega incremental

1. Setup + Foundational → base pronta
2. US1 → validar → já dá pra gravar o vídeo mostrando o fluxo central
3. US2 → validar → identidade visual fecha a percepção de qualidade
4. US3 → validar → assistente para de perder conversa
5. US4 → validar → assistente fecha o ciclo (dado ao vivo + formatação legível)
6. Infra LLM (Phase 7) e Polish (Phase 8) → fecham a exceção de Constituição e a limpeza final

### Estratégia com sub-agentes (autorizado pelo usuário)

Foundational (T001–T004) é sequencial e curta — fazer antes de spawnar. Depois disso, um agente por User Story (US1/US2/US3/US4) mais um para a Phase 7 (Infra LLM) cobre as 5 frentes paralelas listadas acima; Polish (Phase 8) só depois que todas fecharem, porque T043 (quickstart completo) exige tudo funcionando junto.

---

## Notes

- `[P]` = arquivos diferentes, sem dependência pendente
- Rótulo `[Story]` rastreia a tarefa até a User Story do spec.md — Setup/Foundational/Infra/Polish não têm rótulo porque não pertencem a nenhuma
- Cada User Story é completável e testável de forma independente (ver "Independent Test" de cada fase)
- Testes deste tasks.md seguem a convenção já estabelecida no repositório (pytest, Postgres real, sem mock) — não é TDD por pedido explícito do spec, é o padrão que todo o resto do backend já segue
- Evitar: tarefa vaga, dois agentes no mesmo arquivo ao mesmo tempo, dependência entre stories que quebre a independência
