# Tasks: Plataforma Unificada ITSM + Agile

**Input**: Design documents from `/specs/002-unified-itsm-agile-ui/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/)

**Tests**: Incluídos, e não são opcionais aqui. O Princípio IV da constituição exige suíte verde **sem credencial e sem rede** — isso só é verificável com os fakes das integrações novas. Não é TDD completo: cada lógica não trivial deixa um teste, o resto não.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: arquivos diferentes, sem dependência pendente — pode rodar em paralelo
- **[US#]**: história a que a task pertence

## Path Conventions

Web app já existente: `backend/`, `frontend/`, `rag/`. Nenhum diretório de topo novo.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Tokens, configuração e fundação de dados. Nada aqui renderiza tela.

- [X] T001 [P] Portar tokens Nocturne (rampas `neutral`/`accent`/`accent-2` 100–900, `--color-bg|surface|text|divider`, `--space-1..8`, `--radius-sm|md|lg`, `--shadow-sm|md|lg`) para `frontend/src/app/globals.css`, com sobrescrita em `:root[data-theme="light"]` e exposição ao Tailwind via `@theme inline`. Descartar `--color-section*`. No tema claro, texto secundário usa `--color-neutral-600` ou mais escuro — ver [research.md](./research.md) R9
- [X] T002 [P] Trocar Geist por Inter via `next/font/google` e adicionar o script inline anti-FOUC de `data-theme` em `frontend/src/app/layout.tsx`, conforme [contracts/ui-routes.md](./contracts/ui-routes.md)
- [X] T003 [P] Criar `frontend/src/lib/api.ts` com `ApiResult<T>` que nunca lança e nunca exibe corpo de erro do backend cru
- [X] T004 [P] Criar `frontend/src/lib/types.ts` com os tipos de resposta de [data-model.md](./data-model.md)
- [X] T005 [P] Criar `frontend/src/lib/nav.ts` com as seções fechadas de FR-003 e o campo `implemented`
- [X] T006 Adicionar `jira_board_id`, `rag_search_url`, `assistant_enabled`, `assistant_base_url`, `assistant_model`, `assistant_timeout_seconds`, `assistant_max_context_chars`, `openrouter_api_key` e a propriedade `assistant_is_configured` em `backend/app/core/config.py`. Namespace `assistant_*` separado do `llm_*` do classificador de squad
- [X] T007 [P] Adicionar placeholders comentados das variáveis de T006 em `backend/.env.example`
- [X] T008 [P] Criar `backend/app/services/cache.py` — cache TTL em processo, chave `(rota, board_id, params)`, TTL 60 s, invalidação explícita. ~15 linhas, sem dependência ([research.md](./research.md) R7)
- [X] T009 [P] Teste de `backend/app/services/cache.py` em `backend/tests/test_cache.py`: hit dentro do TTL, miss após expirar, invalidação limpa a chave

**Checkpoint**: tokens e configuração prontos. Nada visível ainda.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Primitivas de UI e envelope de erro compartilhados por **todas** as histórias.

**⚠️ CRITICAL**: nenhuma história começa antes desta fase fechar.

- [X] T010 [P] Criar primitivas em `frontend/src/components/ui/`: `card.tsx`, `tag.tsx`, `button.tsx`, `table.tsx`, `stat.tsx` — só tokens, nenhum valor visual literal (FR-006)
- [X] T011 [P] Criar estados em `frontend/src/components/ui/`: `empty-state.tsx`, `error-state.tsx`, `unavailable-state.tsx`, `skeleton.tsx`. `unavailable-state` é distinto de `error-state` — indisponibilidade nomeada não é exceção (FR-030)
- [X] T012 [P] Criar gráficos SVG inline em `frontend/src/components/charts/`: `sparkline.tsx`, `bars.tsx`, `donut.tsx`. Sem biblioteca
- [X] T013 [P] Criar `frontend/src/app/error.tsx`, `loading.tsx` e `not-found.tsx` na raiz
- [X] T014 [P] Criar envelope de indisponibilidade (`available`/`reason`/`detail`/`data`) em `backend/app/domain/agile.py`, conforme [contracts/api-agile.md](./contracts/api-agile.md)
- [X] T015 Adicionar `offset`, `priority`, `squad` e `q` a `GET /workflows` em `backend/app/api/routes.py` e `backend/app/repositories/workflows.py`; `total` passa a contar o recorte filtrado, não a página ([contracts/api-itsm.md](./contracts/api-itsm.md))
- [X] T016 [P] Teste dos filtros combinados e da paginação em `backend/tests/test_workflow_filters.py`: `q` casa assunto e identificador, filtros combinam, `total` reflete o recorte

**Checkpoint**: fundação pronta — as histórias podem começar.

---

## Phase 3: User Story 1 — Shell unificado e Home executiva (P1) 🎯 MVP

**Goal**: Sidebar persistente, troca de workspace por URL, tema com persistência, e uma Home que responde "como está a operação hoje?" com número real.

**Independent Test**: abrir `/`, ler incidentes abertos e progresso do sprint sem orientação; alternar workspace e ver a sidebar trocar sem recarga; alternar tema e recarregar.

- [X] T017 [P] [US1] Criar `frontend/src/components/shell/sidebar.tsx` (servidor) — seções de `lib/nav.ts` filtradas pelo workspace do `pathname`, item ativo com `aria-current="page"`
- [X] T018 [P] [US1] Criar `frontend/src/components/shell/workspace-switcher.tsx` (servidor) — dois `<Link>` para `/itsm` e `/agile`, sem estado
- [X] T019 [P] [US1] Criar `frontend/src/components/shell/theme-toggle.tsx` (cliente) — escreve `data-theme` em `<html>` e em `localStorage`
- [X] T020 [P] [US1] Criar `frontend/src/components/shell/topbar.tsx` (servidor) — título derivado da rota
- [X] T021 [US1] Montar o shell em `frontend/src/app/layout.tsx` compondo T017–T020. Sem route group — todas as rotas usam o mesmo layout
- [X] T022 [US1] Substituir `frontend/src/app/page.tsx` pela Home: indicadores de ITSM de `GET /metrics` e de Agile de `GET /agile/sprint`, cada um com janela de tempo (FR-012) e estado `unavailable` isolado (FR-013)
- [X] T023 [P] [US1] Criar `frontend/src/app/em-construcao/[secao]/page.tsx` — placeholder nomeado único para Assets, Base de Conhecimento, Automações e Administração (FR-004)
- [X] T024 [P] [US1] Criar `frontend/src/app/loading.tsx` da Home como esqueleto do conteúdo, não spinner genérico

**Checkpoint**: US1 funciona sozinha. Agile ainda responde indisponível — e isso é o comportamento correto.

---

## Phase 4: User Story 2 — Operação ITSM: fila e detalhe (P1)

**Goal**: Fila filtrável com exceções destacadas, detalhe com timeline e causa de falha, e reprocessamento.

**Independent Test**: localizar um ticket em falha, abrir o detalhe, entender o motivo e disparar reprocessamento em ≤4 interações a partir da Home.

- [X] T025 [P] [US2] Adicionar `WorkflowDetail`, `TicketDetail`, `TimelineEvent` e `SlaState` a `backend/app/domain/models.py` conforme [data-model.md](./data-model.md)
- [X] T026 [US2] Criar o mapa fechado `event_type → (rótulo, chaves permitidas)` em `backend/app/repositories/workflows.py`. `details_json` **nunca** é devolvido inteiro; `event_type` desconhecido devolve `detail: {}`
- [X] T027 [US2] Implementar `get_workflow_detail()` em `backend/app/repositories/workflows.py` — junta `workflow_executions`, `tickets`, `routing_decisions` (mais recente), `jira_issue_links` e `audit_logs` ordenado por `created_at`; deriva `reprocess_eligible`
- [X] T028 [US2] Adicionar `GET /workflows/{workflow_execution_id}` em `backend/app/api/routes.py`, com `404` quando não existe
- [X] T029 [P] [US2] Teste em `backend/tests/test_workflow_detail.py`: timeline em ordem cronológica, `404` para id inexistente, `reprocess_eligible` correto por status, e **`detail` nunca carrega assunto ou descrição do ticket**
- [X] T030 [P] [US2] Criar `frontend/src/components/itsm/ticket-table.tsx` (servidor) — identificador, assunto, prioridade, status, responsável, SLA, com destaque por exceção (FR-014)
- [X] T031 [P] [US2] Criar `frontend/src/components/itsm/ticket-filters.tsx` (cliente) — escreve em `searchParams` via `router.replace` para o recorte sobreviver à recarga
- [X] T032 [P] [US2] Criar `frontend/src/components/itsm/timeline.tsx` (servidor)
- [X] T033 [US2] Criar `frontend/src/app/itsm/page.tsx` — fila com filtros, busca, total e paginação por `offset` (FR-014 a FR-016). `searchParams` é `Promise`, precisa de `await`
- [X] T034 [US2] Criar `frontend/src/app/itsm/[id]/page.tsx` — detalhe, timeline, issue Jira vinculada, e volta à lista preservando filtros (FR-017, FR-018, FR-021). `params` é `Promise`
- [X] T035 [US2] Mover `frontend/src/app/reprocess-button.tsx` para `frontend/src/components/itsm/` e desabilitá-lo durante a requisição; consumir `reprocess_eligible` da API em vez do `REPROCESS_ELIGIBLE` duplicado no cliente (FR-019, FR-020)
- [X] T036 [P] [US2] Criar `frontend/src/app/itsm/loading.tsx` e `frontend/src/app/itsm/error.tsx`

**Checkpoint**: US1 e US2 funcionam de forma independente.

---

## Phase 5: User Story 3 — Workspace Agile pelo Jira (P2)

**Goal**: Sprint, burndown, bloqueios, velocidade, backlog ranqueado e quadros com transição real.

**Independent Test**: com credencial válida, conferir que sprint e pontos batem com o board no Jira, e mover um card confirmando a mudança de status no próprio Jira.

**Credencial**: resolvida em 2026-07-28 (`JIRA_EMAIL` estava errado). Board descoberto e sondado — ver [research.md R12b](./research.md).

- [x] T037 [US3] ~~Descobrir e gravar `JIRA_BOARD_ID`~~ — **feito**: board `2` (`FRESH board`, team-managed), sprint ativo `id=2`, estimativa em `customfield_10016`. Falta apenas gravar `JIRA_BOARD_ID=2` em `backend/.env`
- [X] T037a [US3] Povoar o board FRESH no Jira **antes da apresentação** — **feito em 2026-07-29 via script contra a API real do Jira** (`evidence/evaluations/2026-07-29-plataforma-unificada-itsm-agile.md`): 19 issues estimadas em `customfield_10016`, 2 épicos (`FRESH-1`, `FRESH-13`) com issues vinculadas, objetivo gravado no sprint ativo (`FRESH Sprint 3`), 2 sprints históricos fechados (`FRESH Sprint 1`=11pts, `FRESH Sprint 2`=18pts) dando série real de velocidade. **Não automatizável**: `max` de coluna (WIP limit) não tem endpoint de escrita na REST API pública do Jira (só a UI de Board Settings edita `columnConfig`) — passo manual restante, documentado abaixo
- [X] T038 [P] [US3] Criar os modelos `BoardConfig`, `BoardColumn`, `Sprint`, `WorkItem`, `Person`, `Epic`, `BurndownSeries`, `VelocityPoint`, `TransitionResult` em `backend/app/domain/agile.py`
- [X] T039 [US3] Criar `JiraAgileClient` em `backend/app/integrations/jira_agile.py` — `get_board_configuration`, `get_active_sprint`, `get_closed_sprints`, `get_sprint_issues`, `get_backlog`, `get_board_issues`, `get_transitions`, `apply_transition`. Campo de estimativa vem de `estimation.field.fieldId`, nunca de variável de ambiente ([research.md](./research.md) R1)
- [X] T040 [P] [US3] Criar `FakeJiraAgileClient` em `backend/app/integrations/jira_agile.py` com fixture determinística e modos de erro `unauthorized`, `forbidden`, `unavailable`, `rate_limited`
- [X] T041 [US3] Implementar `backend/app/services/agile.py`: casar status com coluna, derivar `done_status_ids` da **última** coluna mapeada, calcular `over_wip`, agregar pontos por épico, e montar `Person` com iniciais e cor por hash estável (`avatar_url` sempre `None`)
- [X] T042 [US3] Implementar burndown em `backend/app/services/agile.py` a partir de `expand=changelog`: linha ideal reta, linha real por transição para status de Done, escopo adicionado elevando o comprometido a partir do dia de entrada, dia futuro como `None` ([research.md](./research.md) R3)
- [X] T043 [US3] Implementar velocidade em `backend/app/services/agile.py` — últimos 5 sprints fechados, mais antigo primeiro
- [X] T044 [US3] Implementar a resolução de transição em `backend/app/services/agile.py`: **comparar destino com status atual e devolver `already_there` sem chamar o Jira** (o Jira oferece transição para o próprio status — medido, ver [research.md R12b](./research.md)); senão ler transições disponíveis, casar `to.id` com os status da coluna destino e aplicar; sem correspondência devolve `no_transition` com os nomes alcançáveis
- [X] T045 [US3] Criar `backend/app/api/routes_agile.py` com `GET /agile/sprint`, `GET /agile/backlog`, `GET /agile/board` e `POST /agile/issues/{issue_key}/transition`; montar em `backend/app/api/routes.py`. Todas as leituras usam o cache de T008 e o envelope de T014
- [X] T046 [P] [US3] Teste em `backend/tests/test_jira_agile_client.py` com `respx`: parsing de configuração de board com e sem `max`, `estimation.type != "field"`, e sprint ativo ausente
- [X] T047 [P] [US3] Teste em `backend/tests/test_agile_service.py`: burndown com escopo adicionado, `over_wip` respeitando `constraint_type: "none"`, e agregação de épico com `total_points` zero
- [X] T048 [P] [US3] Teste em `backend/tests/test_agile_routes.py`: credencial ausente devolve `200` com `available: false`; **destino igual ao status atual devolve `already_there` sem chamar o cliente Jira**; transição sem caminho devolve `409` com `available_transitions` preenchido; transição bem-sucedida devolve o status relido do Jira. O fake precisa reproduzir a lista de transições real do board FRESH, que inclui a auto-transição
- [X] T049 [P] [US3] Criar `frontend/src/components/charts/burndown.tsx` — SVG inline, linha ideal e real, dias futuros não desenhados
- [X] T050 [US3] Criar `frontend/src/app/agile/page.tsx` — sprint, burndown, bloqueios, velocidade; estado vazio nomeado quando não há sprint ativo, com acesso ao Backlog (FR-022 a FR-025). Tratar `goal: ""` como ausência de objetivo, e velocidade sem sprint fechado como estado vazio nomeado, não gráfico em branco
- [X] T051 [P] [US3] Criar `frontend/src/components/agile/backlog-table.tsx` e `frontend/src/app/agile/backlog/page.tsx` — ordem de rank do Jira, épico e progresso por épico (FR-026)
- [X] T052 [US3] Criar `frontend/src/components/agile/board.tsx` (cliente) — colunas do board, sinalização de estouro de WIP, drag-and-drop HTML5 nativo, estado otimista com snapshot e reversão em qualquer status ≠ 200 (FR-027 a FR-029, FR-048)
- [X] T053 [US3] Adicionar menu "Mover para" acionável por teclado em `frontend/src/components/agile/board.tsx`, disparando a mesma requisição do arraste — arraste não pode ser o único caminho (FR-008)
- [X] T054 [P] [US3] Criar `frontend/src/app/agile/scrum/page.tsx` (`scope=sprint`) e `frontend/src/app/agile/kanban/page.tsx` (`scope=board`)
- [X] T055 [P] [US3] Criar `loading.tsx` e `error.tsx` em `frontend/src/app/agile/`

**Checkpoint**: US1, US2 e US3 independentes. Desligar o Jira não afeta ITSM nem Home.

---

## Phase 6: User Story 4 — Reports dentro do shell (P2)

**Goal**: O painel analítico existente vira seção do shell, acessível dos dois workspaces, sem perder capacidade.

**Independent Test**: abrir Reports a partir de ITSM e de Agile, aplicar filtros e ver os gráficos responderem; com base vazia, receber o fluxo de ingestão.

- [X] T056 [US4] `git mv frontend/src/app/analytics frontend/src/app/reports` e ajustar imports — preserva histórico
- [X] T057 [US4] Reestilizar `frontend/src/app/reports/page.tsx` com as primitivas de T010–T012, removendo `Stat` e `Bars` locais em favor dos componentes compartilhados. Lógica de dado inalterada
- [X] T058 [P] [US4] Reestilizar `frontend/src/app/reports/filter-bar.tsx` e `upload-screen.tsx` com os tokens; comportamento inalterado
- [X] T059 [US4] Garantir estado vazio explícito por visualização quando o recorte de filtro não retorna linha (FR-035)
- [X] T060 [P] [US4] Criar `loading.tsx` e `error.tsx` em `frontend/src/app/reports/`
- [X] T061 [US4] Apontar a entrada Reports de `lib/nav.ts` para `/reports` nos dois workspaces e remover qualquer link remanescente para `/analytics`

**Checkpoint**: US1 a US4 completas. Só o assistente falta.

---

## Phase 7: User Story 5 — Assistente com respostas fundamentadas (P3)

**Goal**: Pergunta em linguagem natural, resposta com fontes citadas, e recusa explícita quando não há fundamento.

**Independent Test**: perguntar sobre a arquitetura e ver a resposta com fontes abríveis; perguntar fora de domínio e receber recusa em vez de invenção.

- [X] T062 [P] [US5] Criar `rag/http/__init__.py` e `rag/http/app.py` — FastAPI com `POST /search` e `GET /health`, envolvendo `rag.search.query.search()` sem alterá-lo. `results: []` é `200`, banco ausente é `503` ([contracts/rag-search.md](./contracts/rag-search.md))
- [X] T063 [P] [US5] Adicionar `fastapi` e `uvicorn` a `rag/requirements.txt` e a `rag/pyproject.toml`, mantendo os dois em sincronia
- [X] T064 [P] [US5] Adicionar o serviço `rag-search` a `docker-compose.yml` com healthcheck em `/health`, **sem porta publicada** — só a rede interna
- [X] T065 [P] [US5] Teste em `rag/tests/test_http.py`: `query` vazia devolve `422`, pergunta fora de domínio devolve `200` com `total: 0`, banco ausente devolve `503`
- [X] T066 [P] [US5] Criar `backend/app/services/redaction.py` — função pura removendo e-mail, telefone, CPF e nome de solicitante, com marcador estável (`[email]`, `[telefone]`, `[documento]`, `[solicitante]`)
- [X] T067 [P] [US5] Teste em `backend/tests/test_redaction.py` cobrindo cada padrão e confirmando que a frase segue legível
- [X] T068 [P] [US5] Criar `RagSearchClient` e `FakeRagSearchClient` em `backend/app/integrations/rag_search.py`; o fake devolve lista vazia sob demanda para exercitar `no_grounding`
- [X] T069 [P] [US5] Criar `OpenRouterClient` e `FakeAssistantClient` em `backend/app/integrations/openrouter.py` — `httpx` contra `POST {base_url}/chat/completions`, sem SDK. O fake tem modos `rate_limited`, `unavailable`, `timeout`. Mapear `429`, `5xx`, expiração de timeout e corpo malformado para status distintos ([research.md](./research.md) R10)
- [X] T070 [P] [US5] Criar os modelos `AssistantQuestion`, `AssistantAnswer`, `RetrievedSource`, `AssistantMessage` em `backend/app/domain/assistant.py`, com `status` em enum fechado
- [X] T071 [US5] Implementar `backend/app/services/assistant.py` na ordem de [contracts/api-assistant.md](./contracts/api-assistant.md): desligado → recupera → **corta sem chamar o modelo quando zero trecho** → redige. Cada trecho entra envolto em `<untrusted_document>`; texto de ticket passa por `redaction` antes; histórico truncado marca `truncated_history`
- [X] T072 [US5] Criar `backend/app/api/routes_assistant.py` com `POST /assistant/ask` sempre `200` e o resultado em `status`; montar em `backend/app/api/routes.py`. `422` só para `question` vazia ou acima de 2000 caracteres
- [X] T073 [P] [US5] Teste em `backend/tests/test_assistant.py`: recuperação vazia devolve `no_grounding` **sem chamar o cliente do modelo**; cada modo de falha devolve o `status` próprio **com `sources` preenchido**; `ASSISTANT_ENABLED=false` devolve `disabled`; nenhuma resposta carrega chave, modelo ou URL do provedor
- [X] T074 [P] [US5] Criar `frontend/src/components/assistant/message.tsx` e `sources.tsx` — fonte abrível com trecho e origem, renderizada como texto simples, nunca como HTML (FR-037, FR-045)
- [X] T075 [US5] Criar `frontend/src/components/assistant/chat.tsx` (cliente) — entrada, histórico de sessão, estado de carregamento, faixa distinta por `status`, e exibição das fontes mesmo quando `answer` é `null` (FR-043)
- [X] T076 [P] [US5] Criar `frontend/src/app/assistant/page.tsx` com `loading.tsx` e `error.tsx`
- [X] T077 [US5] Estender `rag/golden/` com perguntas do assistente e publicar o número medido. **Só depois disso `ASSISTANT_ENABLED` pode ir a `true`** — condição do Princípio I registrada em [research.md](./research.md) R5

**Checkpoint**: todas as histórias independentes e funcionais.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T078 Registrar ADR do LLM remoto em `docs/ai/ai-decisions.md`: que dado sai da máquina, redação de PII aplicada antes, retenção de prompt pelo provedor em tier gratuito, hardware local insuficiente para modelo de geração grande como motivo, e `ASSISTANT_ENABLED=false` como desligamento. Exigido pela violação registrada no [plan.md](./plan.md)
- [X] T079 Remover `frontend/src/app/analytics/` residual e qualquer sobra da `page.tsx` antiga — código superado sai do disco, não só da navegação (Princípio V)
- [X] T080 [P] Rodar verificação automatizada de acessibilidade em todas as rotas implementadas, nos dois temas; corrigir toda violação A e AA. Conferir explicitamente o item inativo da sidebar no tema claro (SC-005)
- [X] T081 [P] Verificar viewport de 360 px em todas as rotas — tabela e quadro rolam no próprio contêiner, página sem rolagem horizontal (FR-009, SC-006)
- [X] T082 [P] Suprimir transição e animação sob `prefers-reduced-motion` em `frontend/src/app/globals.css` (FR-008)
- [X] T083 Rodar `env -u JIRA_BASE_URL -u JIRA_API_TOKEN -u OPENROUTER_API_KEY make test` e `make rag-test`. Falha aqui significa teste alcançando a rede — corrigir o teste, não a configuração (Princípio IV)
- [X] T084 [P] Auditar log e tráfego: `docker compose logs api` após pergunta ao assistente e após transição de card não pode conter token nem conteúdo de ticket (FR-042, SC-010)
- [X] T085 [P] Atualizar a seção "o que ficou de fora" do `README.md` — SLA sem prazo conhecido, avatar sem imagem, ausência de autenticação, quadros dependentes de credencial viva
- [X] T086 Executar os 14 cenários de [quickstart.md](./quickstart.md) e registrar evidência em `evidence/`

---

## Dependencies & Execution Order

### Phase Dependencies

```
Phase 1 (Setup)
   └─> Phase 2 (Foundational)  ← bloqueia todas as histórias
          ├─> Phase 3 (US1) ─┐
          ├─> Phase 4 (US2)  │
          ├─> Phase 5 (US3)  ├─> Phase 8 (Polish)
          ├─> Phase 6 (US4)  │
          └─> Phase 7 (US5) ─┘
```

### User Story Dependencies

Nenhuma história depende de outra para funcionar. Duas observações práticas:

- **US1** entrega o shell. US2–US5 renderizam **dentro** dele, então convém fazer US1 primeiro — mas cada uma é testável isoladamente por URL direta.
- **US3** já tem credencial e board válidos (T037 fechada). T037a é trabalho de dado no Jira e só bloqueia a **demonstração**, não a implementação: T038–T055 rodam contra o `FakeJiraAgileClient` sem credencial nenhuma.

### Within Each User Story

Backend antes de frontend: modelo → cliente de integração → serviço → rota → tela. Os testes de cada camada acompanham a camada, não o fim da fase.

### Parallel Opportunities

| Fase | Tasks paralelas | Observação |
|---|---|---|
| 1 | T001–T005, T007–T009 | T006 é sequencial (mesmo arquivo de config) |
| 2 | T010–T014, T016 | T015 toca `routes.py` e `workflows.py` |
| 3 | T017–T020, T023, T024 | T021 e T022 dependem de T017–T020 |
| 4 | T025, T029–T032, T036 | T026–T028 encadeiam no mesmo repositório |
| 5 | T038, T040, T046–T049, T051, T054, T055 | T039, T041–T045 encadeiam em `agile.py` |
| 6 | T058, T060 | T056 move diretório — precisa vir primeiro |
| 7 | T062–T070, T073, T074, T076 | T071, T072, T075, T077 encadeiam |
| 8 | T080–T082, T084, T085 | T078, T079, T083, T086 sequenciais |

Times distintos podem tocar US2 (backend Postgres), US3 (integração Jira) e US5 (RAG + LLM) ao mesmo tempo — não compartilham arquivo.

---

## Implementation Strategy

### MVP

**Phase 1 + Phase 2 + Phase 3 (US1)** — 24 tasks. Entrega o shell, a troca de workspace, o tema e a Home com métrica real de ITSM. Já resolve o problema declarado no spec: "duas telas desconexas, sem noção de produto". Agile responde indisponível, o que é o comportamento correto e demonstrável.

### Incremento seguinte

**+ Phase 4 (US2)** — 36 tasks acumuladas. Aqui a plataforma vira ferramenta de trabalho: fila filtrável, detalhe com timeline, reprocessamento. Não depende de nenhuma credencial externa.

### Depois

**US3** quando o token Jira for renovado (T037). **US4** a qualquer momento — é reestilização de código pronto, o incremento mais barato. **US5** por último, e com o portão do golden set em T077.

### Ordem sugerida se o tempo apertar

US1 → US2 → US4 → US3 → US5. US4 custa pouco e adiciona uma seção inteira ao produto; US3 e US5 são as que dependem de terceiro vivo no momento da apresentação.
