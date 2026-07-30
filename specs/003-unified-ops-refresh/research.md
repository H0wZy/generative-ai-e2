# Research: Refresh Operacional

## R1 — Chamado ao vivo reaproveita o pipeline existente, sem worker novo obrigatório

**Decision**: a tela de criação chama `POST /api/v1/tickets/ingest` (já existe) e, na sequência, `POST /api/v1/workflows/process-next` (já existe) uma vez, para processar o evento recém-criado sem esperar o intervalo de poll. Nenhuma rota nova de ingestão.

**Rationale**: `IngestionService`/`ProcessingService`/outbox já implementam exatamente o fluxo pedido (US1) — squad routing determinístico, criação de issue no Jira, retry com backoff, estado nomeado de falha. Construir um segundo caminho duplicaria a única fonte de verdade que a Constituição (Princípio III) exige.

**Aceito como limitação conhecida**: `process-next` reivindica o eventos mais antigo não reivindicado da fila **inteira**, não um evento específico. Em uso de demonstração (um avaliador por vez, per Assumptions do spec.md) a fila está vazia antes da criação, então o evento processado é sempre o que acabou de ser criado. Sob dois chamados quase simultâneos a ordem de processamento ainda é FIFO correta — só a *resposta HTTP* do `process-next` chamado pela tela A poderia, em teoria, descrever o resultado do chamado B se as duas chamadas colidirem no mesmo milissegundo. Dado o Assumption "execução local/demo, não hospedada" (spec.md), não é corrigido nesta feature — documentar como conhecido, não descoberto tardio (Princípio V).

**Alternatives considered**: variante de `process-next` que aceita `workflow_execution_id` alvo — rejeitada por enquanto (YAGNI): resolve uma corrida que só aparece com dois usuários simultâneos, cenário fora do Assumption do spec.

**Docker Compose**: adicionar serviço `worker` (`python -m app.worker --loop`) mesmo assim — não para o caminho síncrono do demo, mas porque hoje **nada** drena `retry_scheduled` fora do gatilho manual, e um chamado que cai em retry (Jira momentaneamente indisponível) ficaria preso para sempre sem ele. Reaproveita a imagem já buildada do `api` (mesmo Dockerfile, comando diferente).

## R2 — Classificador de squad muda de Ollama para OpenRouter, reaproveitando o cliente do assistente

**Decision**: novo `OpenRouterSquadClient` em `app/integrations/llm.py`, implementando o `LLMClientProtocol` já existente. Internamente delega a chamada HTTP para `OpenRouterClient.complete()` (`app/integrations/openrouter.py`) — mesma classe que o assistente já usa — com um prompt que pede JSON estrito, e faz `json.loads()` do conteúdo devolvido do mesmo jeito que `OllamaClient` já faz hoje. `SquadClassification` (Pydantic, validação de enum fechado) não muda — é o ponto de proteção contra saída fora do enum, igual já é hoje (Princípio I).

**Rationale**: evita reimplementar chamada HTTP a provedor — `OpenRouterClient` já resolve timeout, erro de conexão e parsing de resposta. Mantém os dois usos (classificador e assistente) em **namespaces de configuração separados** (`llm_*` vs `assistant_*`), como o ADR-012 já decidiu — a mudança é qual provedor `llm_*` aponta para, não uma fusão das duas configs.

**Config**: `llm_base_url` passa a default para `https://openrouter.ai/api/v1`, `llm_model` para o mesmo modelo Nvidia free do assistente. `OllamaClient` **não é deletado** nesta feature (Princípio V: código sem consumidor sai da navegação antes de sair do disco — mas aqui ele ainda é código válido, só deixa de ser o default; remover a classe é decisão de limpeza separada, fora do escopo motivado por este pedido).

**Gate obrigatório antes de `LLM_ENABLED=true` ser o padrão**: `make routing-eval` reexecutado contra o novo provedor, número publicado em `docs/ai/ai-decisions.md` (ADR-013). Os números do ADR-011 (100% acurácia, 66,67% injeção) são do `qwen3:8b` — Princípio I explicitamente proíbe usar um número medido para outro modelo.

**Alternatives considered**: manter Ollama para o classificador e só o assistente no OpenRouter (status quo) — rejeitada porque foi pedido explícito do usuário (evaluators sem Ollama instalado não conseguiriam rodar o classificador de jeito nenhum, tornando-o `needs_human_review` sempre).

## R3 — Persistência de conversa: sessão sem login, duas tabelas

**Decision**: `assistant_conversations` (PK `session_id: uuid`, `created_at`) e `assistant_messages` (PK `id`, FK `conversation_id`, `role`, `text`, `sources_json`, `created_at`). O frontend gera um UUID uma vez (`crypto.randomUUID()`), grava em `localStorage`, e manda em todo request como header `X-Session-Id`. `GET /api/v1/assistant/conversation` devolve o histórico; `POST /assistant/ask` grava a pergunta e a resposta na mesma transação.

**Rationale**: replica exatamente o "sem login" que já existe no resto da plataforma (nenhuma outra tela tem auth) — mesma confiança já depositada no cliente. Duas tabelas simples, sem TTL/expiração pedido em nenhum FR — não construído (YAGNI).

**Alternatives considered**: cookie de sessão assinado pelo servidor — rejeitado, complexidade de assinatura/rotação não pedida por nenhum FR e o resto do app não tem sessão de servidor nenhuma para se equiparar.

## R4 — Assistente consulta dado de chamado só quando a pergunta cita uma chave Jira

**Decision**: heurística é uma regex de chave de issue Jira (`[A-Z][A-Z0-9]*-\d+`, o mesmo formato de `jira_issue_key`) na pergunta. Quando casa, uma única leitura busca o `WorkflowDetail` por `jira_issue_key` e o resultado é embrulhado em `<untrusted_document source="ticket:{key}">` — mesma função `_wrap()` do RAG, estendida para aceitar essa origem. Segue **exatamente** o padrão FR-038/061: nunca bloqueia, ausência ou não-encontrado só significa "sem esse contexto adicional", nunca erro.

**Rationale**: é a única heurística que consegue apontar para um chamado específico sem ambiguidade. "Status do meu chamado" sem chave não tem como resolver — não há login nem vínculo usuário↔chamado no sistema (spec.md Assumptions). Regex + 1 SELECT é o mínimo que atende FR-060; nenhuma chamada de função ao modelo (explicitamente rejeitado — mesma razão já registrada para o RAG: modelo free tier não decide function-call de forma confiável).

**Alternatives considered**: `source_ticket_id` (UUID interno) como chave de busca alternativa — rejeitado: usuário nunca vê esse UUID na tela, só a `jira_issue_key`; buscar por um identificador que a pessoa nunca digitaria é trabalho morto.

## R5 — Formatação da resposta: parser mínimo, sem dependência nova

**Decision**: um parser pequeno em `frontend/src/lib/markdown.ts` reconhece só `**negrito**`, `*itálico*` e `[texto](href)` — nada além disso (sem títulos, listas, tabelas). `href` só vira `<Link>` clicável se estiver numa allow-list derivada de `NAV` (`frontend/src/lib/nav.ts`, apenas itens `implemented: true`); qualquer outro valor renderiza como texto do link, sem navegação. O parser roda **só** sobre `answer` (texto do próprio assistente) — nunca sobre `sources[].content` ou o contexto de ticket, que continuam texto puro (FR-064, FR-045 inalterado).

**Rationale**: nenhuma lib de Markdown está instalada (`frontend/package.json` não tem `react-markdown`/`marked`/similar) e a superfície pedida é 3 padrões — trazer uma dependência de Markdown completa (parsing de HTML embutido, tabelas, footnotes) para renderizar negrito/itálico/link seria a definição de overengineering que o próprio brainstorming identificou. O allow-list de rota é defesa em profundidade: mesmo que o modelo alucine um `href` fora do allowlist, nada navega para lá.

**System prompt**: instruído a emitir link de navegação só como `[texto](/rota)` de uma lista curta de rotas reais anexada ao prompt (mesmas rotas de `NAV`), nunca como URL livre.

**Alternatives considered**: `react-markdown` + `rehype-sanitize` — rejeitado (dependência nova para 3 padrões, ladder rung 5/6 do projeto pede reuso antes de dependência nova).

## R6 — Identidade visual: troca de token, não de componente

**Decision**: os hex novos (`#141414`/`#1c1c1c`/`#333331`/`#8a8a86`/`#edebe6`/`#c9a227` + `ok`/`warn`/`crítico`) substituem os valores em `frontend/src/app/globals.css` (`:root` e `:root[data-theme="light"]`), dentro do sistema `@theme inline` já existente. Nenhum componente muda de classe Tailwind — todos já consomem `text-text`, `bg-surface`, `text-muted` etc., que são os tokens semânticos, não hex cru.

**Rationale**: specs/002 já fez esse desenho (research.md R9) — é a mesma arquitetura, só troca de valor. O "trilho de status" (3px na borda esquerda) já existe como padrão visual em `Tag`/linha de tabela (ver `frontend/src/app/itsm/[id]/page.tsx`, `<Tag tone="danger|success">`) — extensão é aplicar a mesma borda em `TicketTable` e nos cards do Kanban/Scrum, reaproveitando o componente `Tag` em vez de criar um novo.

**Tema claro**: os pares de contraste precisam ser remedidos com os hex novos (não é herdado automaticamente do tema escuro) — mesma disciplina que specs/002 já documentou (FR-008, SC-005 daquela feature).

## R7 — Reports sai do disco, não só da navegação

**Decision**: remover `frontend/src/app/reports/`, o item `Reports` de `NAV`, e o backend correspondente: rotas `/api/v1/analytics/*` em `routes.py`, `app/services/analytics/`, e os testes `test_analytics_*.py`.

**Rationale**: nada mais consome esse código depois que a tela sai da navegação — deixá-lo no disco seria exatamente o "código superado" que o Princípio V pede para tirar. FR-032 a FR-035 (specs/002) já estão marcados como supersedidos no spec.md desta feature.

**Fixtures/exemplos**: `examples/*.json` usados só pelos testes de analytics saem junto; nenhum outro teste referencia esses arquivos (verificado por grep antes da remoção, na fase de tasks).
