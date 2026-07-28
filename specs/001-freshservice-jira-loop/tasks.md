---
description: "Task list for 001-freshservice-jira-loop"
---

# Tasks: Loop fechado Freshservice → Jira com medição do ganho

**Input**: Design documents from `/specs/001-freshservice-jira-loop/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: incluídos. A constituição exige suíte verde sem rede e sem
credencial (princípio IV), e validação por execução real (`qa-dev`). Testes
não são opcionais aqui.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: pode rodar em paralelo (arquivos diferentes, sem dependência pendente)
- **[Story]**: US1..US4, conforme as user stories da spec

## Path Conventions

Backend em `backend/`, frontend em `frontend/`. Caminhos abaixo são relativos
à raiz do repositório.

---

## Phase 1: Setup

**Purpose**: dependências e configuração compartilhadas. Nada de lógica.

- [x] T001 Adicionar `pandas`, `openpyxl` e `python-multipart` às dependências em `backend/pyproject.toml` (justificativa já registrada em Complexity Tracking do plan.md)
- [x] T002 [P] Substituir `JIRA_PROJECT_IDENTITY`/`_FINANCE`/`_PLATFORM` por `JIRA_PROJECT_KEY` e acrescentar `FRESHSERVICE_DOMAIN`, `FRESHSERVICE_API_KEY`, `FRESHSERVICE_POLL_INTERVAL_SECONDS` em `backend/.env.example`, todos como placeholder comentado
- [x] T003 [P] Adicionar alvos `poll-once` e `analytics-load` ao `Makefile`, no mesmo padrão de `worker-once`
- [x] T004 [P] Garantir que exports reais do Power BI não entrem no repositório: regra para `examples/*.xlsx` e `examples/*.csv` no `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: enum de squad, configuração e migration operacional. Bloqueia US1 e US4.

**⚠️ CRITICAL**: nenhuma user story começa antes desta fase fechar.

- [x] T005 Criar `backend/app/domain/squads.py` com o enum fechado das 13 squads reais (Squad1, Squad2, Squad4, Squad5, Squad6, Squad8, Datastage, Fresh, GCP, RPA, STD, VSSPS, WordPress) e uma função de normalização (trim, caixa, acento) que devolve `None` para valor fora do enum
- [x] T006 Atualizar `backend/app/core/config.py`: remover `jira_project_identity`/`_finance`/`_platform`, adicionar `jira_project_key`, `freshservice_domain`, `freshservice_api_key` (`SecretStr`), `freshservice_poll_interval_seconds`, e a propriedade `freshservice_is_configured` espelhando `jira_is_configured`
- [x] T007 Criar migration `backend/migrations/versions/002_link_origin.py`: coluna `tickets.squad` (varchar 40, nula), coluna `jira_issue_links.link_origin` (varchar 20, não nula, default `'deterministic'`, `CHECK IN ('deterministic','best_effort')`) e tabela `sync_state` (`source` text PK, `last_sync_at` timestamptz)
- [x] T008 Refletir as colunas e a tabela de T007 em `backend/app/repositories/schema.py`
- [x] T009 [P] Criar helper de categorização de erro em `backend/app/integrations/errors.py` com as três categorias de R-007 (`auth`, `connectivity`, `business`), sem jamais incluir credencial ou corpo de resposta na mensagem

**Checkpoint**: base pronta. US1 e US4 podem começar; US2 é independente e já podia ter começado.

---

## Phase 3: User Story 1 — Tombamento automático (Priority: P1) 🎯 MVP

**Goal**: chamado aberto no Freshservice vira issue no backlog da squad certa, sem ação humana, com vínculo estruturado.

**Independent Test**: abrir um chamado no sandbox do Freshservice e verificar, sem tocar em nada, que a issue existe no projeto Jira com o rótulo do chamado e o rótulo da squad.

### Tests for User Story 1

> Escrever antes da implementação e confirmar que falham.

- [x] T010 [P] [US1] Teste de roteamento determinístico com squad real preenchida em `backend/tests/test_routing.py`: `squad="Squad4"` → `squad_id="Squad4"`, `confidence=1.0`, `rule_version="routing-rules/v2"`, sem chamada ao LLM
- [x] T011 [P] [US1] Teste de squad ausente e de squad fora do enum em `backend/tests/test_routing.py`: ambos → `needs_human_review=True` com `LLM_ENABLED=false`
- [x] T012 [P] [US1] Teste do payload Jira em `backend/tests/test_jira_client.py`: `labels` contém `freshservice-<source_ticket_id>`, `trace-<uuid>` e `squad-<squad_id>`, e `project.key` é o `JIRA_PROJECT_KEY` único
- [x] T013 [P] [US1] Teste de prompt injection em `backend/tests/test_llm_routing.py`: ticket instruindo o modelo a escolher outra squad não produz criação automática — saída fora do enum cai em revisão humana
- [x] T014 [P] [US1] Testes do poller com `respx` em `backend/tests/test_freshservice_client.py`: página com resultados, página vazia, paginação, 401 (`auth`), 429 com `Retry-After` e timeout (`connectivity`)
- [x] T015 [P] [US1] Teste em `backend/tests/test_freshservice_client.py` de que `sync_state.last_sync_at` só avança depois da página inteira persistida, e que reler o mesmo ticket sem mudança devolve `duplicate`
- [x] T016 [P] [US1] Teste em `backend/tests/test_processing.py` de que `link_origin='deterministic'` é gravado ao concluir o vínculo

### Implementation for User Story 1

- [x] T017 [US1] Reescrever `backend/app/services/routing.py`: `route_ticket(squad)` lê o campo de squad do chamado usando o enum de T005; remover `CATEGORY_TO_SQUAD`; `RULE_VERSION = "routing-rules/v2"`. Função continua pura, sem I/O
- [x] T018 [US1] Em `backend/app/domain/models.py`: acrescentar `squad: str | None` (máx. 40) a `TicketIngestRequest`, `link_origin` a `WorkflowListItem`, e `squad` a `TicketRecord`
- [x] T019 [US1] Em `backend/app/services/processing.py`: trocar `_squad_project_key()` por uma função de destino que devolve `settings.jira_project_key` mais o `squad_id`, mantendo a falha explícita quando a squad não tem destino configurado; passar a squad do ticket para `route_ticket()`
- [x] T020 [US1] Em `backend/app/integrations/jira.py`: acrescentar `squad-<squad_id>` aos `labels` e receber o `squad_id` na assinatura de `create_issue` (atualizar `JiraClientProtocol` e `FakeJiraClient` junto)
- [x] T021 [US1] Em `backend/app/repositories/workflows.py`: persistir `tickets.squad` na ingestão e `jira_issue_links.link_origin='deterministic'` em `complete_with_jira_link`
- [x] T022 [US1] Atualizar o enum de squad em `backend/app/integrations/llm.py` e criar `backend/app/prompts/squad_classifier_v2.txt` com os 13 valores + `unknown`, mantendo o bloco delimitado de conteúdo não confiável
- [x] T023 [US1] Reescrever `backend/tests/golden/routing_golden.jsonl` para as squads reais: mínimo 15 casos, ao menos 2 que devem resultar em abstenção e 1 de prompt injection
- [x] T024 [US1] Ajustar `backend/scripts/routing_eval.py` ao enum novo e conferir que `make routing-eval` continua fora de `make test`
- [x] T025 [US1] Criar `backend/app/integrations/freshservice.py`: cliente de leitura com Basic Auth, `GET /api/v2/tickets?updated_since=`, paginação, mapeamento de campos conforme `contracts/external.md`, e categorização de erro via T009. Incluir o dublê de teste no mesmo padrão do `FakeJiraClient`
- [x] T026 [US1] ~~Confirmar no tenant sandbox o nome real do campo de squad~~ — bloqueado: API key do Freshservice nunca liberada pelo admin do tenant, e replicar o tenant real do cliente é inviável. Decisão (2026-07-28): rodar contra um **mock**, com enum genérico de 8 squads (`SQUAD-01`..`SQUAD-08`) em vez das 13 squads reais do cliente. Campo fixado em `squad` (nativo, mock) — sem lista de candidatos, porque o formato é nosso. Ver D2 em `spec.md` e ADR em `docs/ai/ai-decisions.md`
- [x] T027 [US1] Em `backend/app/worker.py`: laço de polling no intervalo configurado, alimentando o `IngestionService` existente e avançando `sync_state` só após persistir a página
- [x] T028 [US1] Atualizar a fixture de `make ingest-demo` para incluir o campo `squad`

**Checkpoint**: tombamento fim a fim funcionando, com dublê e com sandbox. MVP entregável.

---

## Phase 4: User Story 2 — Carga da base histórica (Priority: P2)

**Goal**: os três arquivos exportados do Power BI viram a base "antes", anonimizados e sem duplicar.

**Independent Test**: subir os três arquivos reais, conferir 393 / 2.629 / 428 no preview e 3.022 chamados + 428 cards gravados; recarregar não altera o total.

**Nota**: independente de US1 — pode ser feita em paralelo por outra pessoa.

### Tests for User Story 2

- [x] T029 [P] [US2] Testes de detecção por assinatura de coluna em `backend/tests/test_analytics_upload_detection.py`: os três tipos, `unknown`, `unreadable` e `too_large`, e a garantia de que o nome do arquivo não influencia
- [x] T030 [P] [US2] Testes da extração do identificador do chamado em `backend/tests/test_analytics_ingestion.py`: prefixo explícito vence, número solto único vale, dois números soltos não vinculam, hífen non-breaking e travessão são aceitos
- [x] T031 [P] [US2] Teste do descarte de linha de rodapé em `backend/tests/test_analytics_ingestion.py`: a contagem é 3.022, não 3.024
- [x] T032 [P] [US2] Testes de anonimização em `backend/tests/test_analytics_anonymization.py`: mesmo nome gera o mesmo pseudônimo, nomes diferentes geram pseudônimos diferentes, e nenhum valor original sobrevive na linha a persistir
- [x] T033 [P] [US2] Teste de integração do upsert em lote em `backend/tests/test_analytics_upsert.py` contra Postgres real, com 4.001 linhas — regressão do limite de 65.535 parâmetros bind
- [x] T034 [P] [US2] Teste de idempotência da carga em `backend/tests/test_analytics_upsert.py`: segunda carga dos mesmos dados resulta em zero inserção

### Implementation for User Story 2

- [x] T035 [US2] Criar migration `backend/migrations/versions/003_analytics_schema.py`: schema `analytics` com `chamados_abertos` (27 colunas + `synced_at` timestamptz + `anonymized`), `chamados_fechados` (28 + as mesmas duas) e `jira_cards` (15 + `freshservice_ticket_id`, `synced_at`, `anonymized`), com unicidade de `source_id` e `issue_key`
- [x] T036 [P] [US2] Portar `detect_file_type` e `MAX_UPLOAD_BYTES` de `data-receiver/backend-python/app/upload_detection.py` para `backend/app/services/analytics/upload_detection.py`
- [x] T037 [US2] Criar `backend/app/services/analytics/anonymization.py`: pseudônimo determinístico para os campos de pessoa, aplicado antes de qualquer `INSERT`
- [x] T038 [US2] Portar `classify_columns`, `_upsert` (lotes de 1.000), `parse_cell_date`, `parse_jira_date`, `extract_freshservice_ticket_id`, `_TICKET_ID_RE` e `strip_ticket_prefix` de `data-receiver/backend-python/app/` para `backend/app/services/analytics/excel_ingestion.py`, apontando para o schema `analytics` e chamando T037 antes de gravar
- [x] T039 [US2] Refletir as tabelas de T035 em `backend/app/repositories/schema.py`
- [x] T040 [US2] Acrescentar `POST /analytics/upload/detect`, `POST /analytics/upload/commit` e `GET /analytics/data-status` em `backend/app/api/routes.py`, conforme `contracts/api.md` — commit por arquivo em transação própria
- [x] T041 [US2] Definir schemas de resposta de upload e de status em `backend/app/domain/models.py`

**Checkpoint**: base "antes" carregada, anonimizada e idempotente.

---

## Phase 5: User Story 3 — Painel de comparação (Priority: P3)

**Goal**: cobertura de vínculo das duas origens e indicadores de fluxo, filtráveis.

**Independent Test**: com base histórica carregada e ao menos um lote tombado, `GET /analytics/link-coverage` devolve ≈0,729 para best-effort e 1,0 para determinístico.

**Depende de**: US1 (produz o vínculo determinístico) e US2 (produz o histórico).

### Tests for User Story 3

- [x] T042 [P] [US3] Testes de filtro e cascata em `backend/tests/test_analytics_filters.py`, sem banco: um campo não estreita a si mesmo, `sistema` estreita `tecnologia`, filtro do Jira não vaza para o Freshservice
- [x] T043 [P] [US3] Teste do rótulo sintético "Não resolvido" em `backend/tests/test_analytics_filters.py`: filtra `resolution IS NULL`, não compara string
- [x] T044 [P] [US3] Teste de throughput em `backend/tests/test_analytics_indicators.py`: conta `Resolution = "Done"` exatamente — 291 na base de exemplo, não 241 nem 290
- [x] T045 [P] [US3] Teste de lead time em `backend/tests/test_analytics_indicators.py`: média e mediana, `amostras` sobre o dataset filtrado inteiro, chamado sem vínculo fora do cálculo
- [x] T046 [P] [US3] Teste de cobertura em `backend/tests/test_analytics_indicators.py`: as duas origens contadas separadamente por `link_origin`

### Implementation for User Story 3

- [x] T047 [P] [US3] Portar `fetch_chamados`, `fetch_enriched_cards` (regra "fechados vencem") e `bucket_by_period` de `data-receiver/backend-python/app/card_enrichment.py` para `backend/app/services/analytics/enrichment.py`
- [x] T048 [US3] Portar `_apply_common_filters`, `_group_options` (leave-one-out), `UNRESOLVED_LABEL` e os três indicadores de `data-receiver/backend-python/app/routers/squad_indicators.py` para `backend/app/services/analytics/indicators.py`, como funções de serviço sem rota acoplada
- [x] T049 [US3] Implementar a cobertura por origem em `backend/app/services/analytics/indicators.py`, lendo `jira_issue_links.link_origin` para o lado determinístico e `analytics.jira_cards.freshservice_ticket_id` para o best-effort
- [x] T050 [US3] Acrescentar `GET /analytics/filter-options`, `/throughput`, `/distribuicao-trabalho`, `/lead-time` e `/link-coverage` em `backend/app/api/routes.py`, conforme `contracts/api.md`
- [x] T051 [US3] Definir os schemas de resposta dos indicadores em `backend/app/domain/models.py`, incluindo a contagem de itens considerados quando o cálculo exclui parte da base (FR-020)

**Checkpoint**: o número da apresentação existe e é consultável por API.

---

## Phase 6: User Story 4 — Fila de exceções e reprocessamento (Priority: P3)

**Goal**: o que a automação não tombou fica visível, explicado e recuperável.

**Independent Test**: forçar falha de integração, ver o item na fila com motivo, reprocessar e confirmar uma única issue no destino.

**Nota**: `GET /workflows`, `POST /workflows/{id}/reprocess` e `GET /metrics` **já existem e têm teste**. Esta fase é regressão a preservar mais dois ajustes.

- [x] T052 [P] [US4] Confirmar por execução que os testes existentes de reprocessamento (`already_linked`), DLQ e métricas continuam verdes após US1 — se quebraram, o culpado é a mudança de assinatura de T019/T020
- [x] T053 [US4] Expor `link_origin` em `WorkflowListItem` no serializador de `backend/app/api/routes.py`
- [x] T054 [P] [US4] Teste em `backend/tests/test_workflows_dashboard.py` de que a fila distingue as três categorias de erro de R-007 e não exibe credencial, `requester`, descrição bruta nem saída bruta do modelo

**Checkpoint**: falha visível e recuperável, sem vazamento.

---

## Phase 7: Frontend

**Purpose**: camada visual de US2 e US3. Nenhuma regra de negócio nova.

- [x] T055 [P] Tela de carga em `frontend/src/`: `hasData=false` mostra o uploader no lugar do painel; falha de conexão mostra erro com botão de nova tentativa, nunca "Carregando..." eterno
- [x] T056 [P] Aba de comparação em `frontend/src/` consumindo `/analytics/link-coverage`, com as duas coberturas lado a lado
- [x] T057 Barra de filtros em `frontend/src/` com os dois grupos (Freshservice e Jira), sem campo em destaque, botão de limpar e limpeza automática de valor que saiu das opções
- [x] T058 Abas de throughput, distribuição de trabalho e lead time em `frontend/src/`, todas respeitando a mesma barra de filtros

---

## Phase 8: Polish & Cross-Cutting

- [x] T059 Rodar o roteiro completo de `specs/001-freshservice-jira-loop/quickstart.md` e registrar as saídas reais (não afirmações) como evidência
- [x] T060 [P] Registrar prompts, avaliações e latências em `docs/ai/` e `evidence/`, sanitizados
- [x] T061 [P] ADR em `docs/ai/ai-decisions.md` para as três decisões estruturais: squad vinda da origem (R-001), polling em vez de webhook (R-003) e projeto único com rótulo (R-002)
- [x] T062 Atualizar a seção "o que ficou de fora" do `README.md`: o que esta feature mudou, mais a limitação de R-005 (pseudônimo não é anonimato forte) e a dependência do intervalo de polling em SC-002
- [x] T063 Atualizar `docs/handoffs/freshservice-jira.md` e `docs/architecture/operational-contract.md` para refletir polling em vez de webhook — os dois documentos ainda descrevem o fluxo com n8n
- [x] T064 Revisão do `cybersec`: segredo, PII, vazamento em log/DLQ/evidência, e a superfície nova de upload
- [x] T065 Checagem manual de SC-007 com dashboard, fila e dump de log abertos, antes de considerar a feature pronta

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sem dependência
- **Foundational (Phase 2)**: depende de Setup; bloqueia US1 e US4
- **US1 (Phase 3)**: depende de Foundational
- **US2 (Phase 4)**: depende só de T001 (dependências) — **paralela a US1**
- **US3 (Phase 5)**: depende de US1 e US2
- **US4 (Phase 6)**: depende de US1
- **Frontend (Phase 7)**: depende de US2 e US3
- **Polish (Phase 8)**: depende de tudo que for entregue

### Caminho crítico

```text
T001 → T005..T009 → US1 (T010..T028) → US3 (T042..T051) → Frontend → Polish
                 └→ US2 (T029..T041) ─┘
                    US4 (T052..T054) depende só de US1
```

### Paralelismo real

- T002, T003, T004 juntos, depois de T001
- T010 a T016 juntos (arquivos de teste diferentes)
- T029 a T034 juntos
- T042 a T046 juntos
- US1 e US2 por pessoas diferentes, sem conflito de arquivo: US1 mexe em `routing.py`, `processing.py`, `jira.py`, `worker.py`; US2 mexe só em `services/analytics/` e migrations. O único encontro é `api/routes.py` (T040) e `domain/models.py` (T018/T041) — coordenar esses dois

---

## Implementation Strategy

### MVP (US1 apenas)

1. Phase 1 + Phase 2
2. Phase 3 até T024 (tudo com dublê, sem credencial)
3. **PARAR e VALIDAR**: `make test` verde, `make ingest-demo` + `make worker-once` produzindo issue com os três rótulos
4. T025..T028 quando a chave do sandbox existir

Nesse ponto a dor central está resolvida e demonstrável, sem nenhuma linha de
frontend e sem a base histórica.

### Entrega incremental

1. MVP (US1) → tombamento automático funciona
2. + US2 → base "antes" existe
3. + US3 → o ganho vira número
4. + US4 → operação segura da exceção
5. + Frontend → o número vira tela

Cada passo entrega valor sem quebrar o anterior.

---

## Notes

- Escrever o teste antes e confirmar que falha; a suíte inteira roda sem rede e sem credencial
- `make routing-eval` exige Ollama e nunca entra em `make test`
- T026 era confirmação contra o tenant real; virou decisão de produto (mock + squads genéricas) quando o acesso ao tenant real se mostrou inviável — ver a task e D2 em `spec.md`
- Commit por task ou por grupo lógico; parar em qualquer checkpoint é seguro
- FR-006, FR-007, FR-008, FR-022, FR-023 e FR-024 já estão implementados — preservá-los é tarefa de regressão (T052), não trabalho novo
