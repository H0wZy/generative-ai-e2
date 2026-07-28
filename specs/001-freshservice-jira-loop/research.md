# Research — Fase 0

Decisões tomadas antes do design, com o que foi descartado e por quê.
Fonte de verdade inspecionada: `backend/app/` deste repositório e
`backend-python/app/` do projeto `data-receiver` (branch
`feat/backend-python-migration`).

---

## R-001 — De onde vem a squad

**Decision**: a squad de destino vem do campo `Squad` do próprio chamado
Freshservice. `CATEGORY_TO_SQUAD` é removido.

**Rationale**: o mapeamento atual (`access → identity`, `billing → finance`,
`incident/integration → platform`) é sintético; nenhuma dessas squads existe no
ambiente real. O export do Power BI mostra que `Squad` já é uma coluna
preenchida do chamado — 13 valores reais (Squad1, Squad2, Squad4, Squad5,
Squad6, Squad8, Datastage, Fresh, GCP, RPA, STD, VSSPS, WordPress). Ler um
campo que já existe é mais determinístico, mais barato e mais auditável do que
inferir a squad a partir da categoria. `route_ticket()` continua puro e sem
I/O; muda a entrada, não a natureza da função.

**Alternatives considered**:
- *Manter categoria → squad, com as squads reais no lado direito*: exigiria
  inventar um mapeamento categoria → squad que ninguém no ambiente real usa, e
  perderia a informação que o chamado já carrega.
- *Classificar sempre por LLM*: viola o princípio I e transfere para o texto do
  chamado uma decisão que a fonte já traz estruturada.

**Consequência para o LLM**: o fallback continua existindo, agora para o caso
"campo `Squad` vazio ou com valor fora do enum". O enum do prompt sobe para
13 valores + `unknown`, o que torna o golden set atual (`identity`, `finance`,
`platform`) obsoleto — precisa ser reescrito antes de qualquer ativação. Com
mais valores no enum, a acurácia medida provavelmente cai; o limiar de 80% do
Bloco 2 continua valendo como critério de ativação, e `LLM_ENABLED=false`
continua o padrão até o número existir.

---

## R-002 — Destino no Jira: um projeto, squad como rótulo

**Decision**: uma variável `JIRA_PROJECT_KEY`. A squad vai como rótulo (`label`)
da issue. As variáveis `jira_project_identity` / `_finance` / `_platform` saem
de `core/config.py`, e `_squad_project_key()` em `processing.py` some.

**Rationale**: `JiraClient.create_issue()` já monta `labels` com
`freshservice-{source_ticket_id}` e `trace-{correlation_id}`. Acrescentar
`squad-{squad_id}` é uma linha. Criar e manter 13 projetos num trial do Jira
Cloud é trabalho de configuração sem ganho de demonstração, e cada projeto novo
viraria mais uma variável de ambiente e mais um caminho de falha
(`no_project_key_for_squad`).

**Alternatives considered**:
- *13 projetos, um por squad*: máxima fidelidade, custo de configuração alto,
  risco de limite do trial. Descartado com o usuário.
- *Campo customizado de squad em vez de rótulo*: exige criar campo customizado
  no sandbox e descobrir seu `customfield_NNNNN`. Rótulo funciona em qualquer
  projeto sem configuração prévia. Pode virar componente depois, sem mudança de
  contrato interno.

**Nota**: o mapeamento squad → destino permanece uma função isolada, ainda que
hoje devolva sempre o mesmo projeto. É o ponto de extensão para o dia em que o
destino variar — e mantém `no_destination_for_squad` como falha explícita
quando a squad não tiver destino configurado (edge case da spec).

---

## R-003 — Como o chamado chega: polling, não webhook

**Decision**: um poller consulta a API do Freshservice por chamados atualizados
desde a última sincronização e alimenta o mesmo `IngestionService` que hoje
recebe `POST /tickets/ingest`. O webhook fica fora desta feature.

**Rationale**: o Freshservice sandbox é um serviço em nuvem; para ele entregar
um webhook, a API local precisaria estar publicamente acessível — túnel
(ngrok/cloudflared) mais autenticação de boundary que o MVP não tem. O README
já registra "superfície sem autenticação" como limitação aceita apenas por ser
execução local; expor a ingestão à internet invalidaria essa aceitação. Polling
mantém a superfície local, elimina o segredo de assinatura de webhook e
reaproveita o padrão `updated_since` + marca de sincronização que o
`data-receiver` já usa nos connectors.

**Alternatives considered**:
- *Webhook + túnel*: mais fiel a produção, mas obriga autenticação de boundary,
  gestão de segredo de assinatura e um processo externo rodando. Fora de escopo.
- *n8n como adaptador*: continua desenhado no contrato operacional e continua
  não construído; adicionaria um serviço a manter sem resolver o problema da
  exposição.

**Consequência**: SC-002 ("menos de 1 minuto entre abertura e issue visível")
passa a depender do intervalo de polling. O intervalo precisa ser menor que o
alvo — 30 s é suficiente e não é agressivo para um tenant sandbox.

---

## R-004 — Reuso do `data-receiver`: o que entra, o que fica

**Decision**: portar por cópia adaptada, não por dependência entre repositórios.

| Origem (`data-receiver/backend-python/app/`) | Destino | O que muda |
|---|---|---|
| `upload_detection.py` (`detect_file_type`, `MAX_UPLOAD_BYTES`) | `analytics/upload_detection.py` | Nada de substancial |
| `ingestion.py` (`classify_columns`, `_upsert`, `parse_cell_date`, `parse_jira_date`, `extract_freshservice_ticket_id`, `_TICKET_ID_RE`) | `analytics/excel_ingestion.py` | Tabelas passam para o schema `analytics`; upsert em lote de 1.000 linhas preservado |
| `card_enrichment.py` (`fetch_chamados`, `fetch_enriched_cards`, `bucket_by_period`) | `analytics/enrichment.py` | Regra "fechados vencem" preservada |
| `routers/squad_indicators.py` (`_apply_common_filters`, `_group_options`, `UNRESOLVED_LABEL`) | `analytics/indicators.py` | Vira função de serviço; a rota é montada em `api/routes.py` |
| `util.py` (`strip_ticket_prefix`) | `analytics/excel_ingestion.py` | Nada |

**Fica de fora**: toda a trilha C# (`src/`), `routers/ai.py` (a classificação
por Groq — este projeto usa modelo local e o endpoint nunca foi validado contra
o Groq real), e os endpoints antigos já superados no próprio `data-receiver`
(`/api/indicators/agil`, `/api/indicators/relacao`, `/api/summary`).

**Rationale**: o código portado já foi validado contra os arquivos reais e
contra um Postgres real — 3.022 chamados, 428 cards, MTRS recomputado de forma
independente batendo com a API. Reescrever seria refazer a validação. Cópia
adaptada em vez de pacote compartilhado porque são dois repositórios com ciclos
de vida diferentes e nenhum plano de publicar biblioteca.

**Alternatives considered**:
- *Importar `data-receiver` como dependência de caminho*: acopla dois
  repositórios que ninguém versiona junto, e arrasta o backend C# no mesmo
  clone.
- *Chamar o `data-receiver` por HTTP*: dois serviços, dois bancos, e a
  comparação antes/depois precisaria de join entre processos.

---

## R-005 — Anonimização da base histórica

**Decision**: pseudônimo determinístico na entrada. Campos de pessoa
(`Solicitante`, `Agente/Técnico`, `Reporter`, `Assignee`, e-mail) são
substituídos por um identificador estável derivado do valor original antes de
qualquer `INSERT`. O valor original nunca é persistido.

**Rationale**: o export vem de um ambiente corporativo real. O princípio IV e o
FR-016 proíbem que a pessoa identificável entre no banco, na evidência ou na
demonstração. Pseudônimo determinístico (mesmo nome → mesmo identificador)
preserva o que os indicadores precisam — distribuição por responsável, cascata
de filtros — sem preservar a identidade.

**Alternatives considered**:
- *Descartar as colunas de pessoa*: mataria a distribuição de trabalho por
  responsável, que é um dos três indicadores portados.
- *Anonimizar só na exibição*: o dado real ficaria no banco e vazaria em
  qualquer dump, log de erro ou screenshot. Contraria FR-016, que exige a
  anonimização antes da persistência.

**Nota de honestidade**: pseudônimo não é anonimato forte — quem tiver o
arquivo original consegue reverter por comparação. É proteção adequada para uma
base de demonstração local, não para publicação. Registrar essa limitação na
seção "o que ficou de fora" do README.

---

## R-006 — Como a origem do vínculo é representada

**Decision**: uma coluna `link_origin` em `jira_issue_links` com dois valores
(`deterministic`, `best_effort`), e a mesma noção materializada do lado
histórico em `analytics.jira_cards.freshservice_ticket_id`.

**Rationale**: a comparação antes/depois é o produto desta feature. Ela precisa
ser uma consulta, não uma planilha à parte. Com a origem gravada, a cobertura
de cada população é `COUNT` com `GROUP BY` — e a métrica sobrevive a
reprocessamento.

**Alternatives considered**:
- *Inferir a origem pela tabela em que o vínculo está*: funciona hoje, quebra no
  dia em que um chamado histórico for tombado pela automação — exatamente o
  cenário de demonstração mais interessante.

---

## R-007 — Falha de credencial × falha de rede × falha de negócio

**Decision**: `JiraClientError` e o novo `FreshserviceClientError` classificam a
causa em três categorias antes de virar `last_error`: `auth` (401/403),
`connectivity` (timeout, DNS, recusa de conexão, resposta de proxy) e
`business` (o resto). `auth` e `connectivity` nunca gravam a credencial nem o
corpo da resposta.

**Rationale**: FR-027. O `data-receiver` documenta um caso concreto — o proxy
corporativo (Zscaler) devolvendo 403 para `api.groq.com`, que parecia erro de
autenticação e era bloqueio de rede. Sem a distinção, o operador debuga a chave
errada por horas.

**Alternatives considered**:
- *Uma categoria só, com a mensagem HTTP crua*: é o comportamento de hoje
  (`terminal:HTTP 403`) e reproduz exatamente a confusão descrita acima.

---

## R-008 — Linha de base do esforço manual

**Decision**: não bloquear a implementação. O ganho é reportado por cobertura de
vínculo (SC-001) e tempo de ciclo (SC-006), ambos observáveis na base
existente. A medição do tempo manual por chamado é registrada como coleta de
campo paralela.

**Rationale**: o número "quantos minutos o Scrum Master gasta por chamado" só
existe medindo com pessoas, e nada no código depende dele. Bloquear cinco
fatias de implementação por um dado de entrevista seria inverter a prioridade.

---

## Riscos abertos

| Risco | Impacto | Mitigação |
|---|---|---|
| Credenciais de sandbox ainda não obtidas | F2 não fecha | F1, F3 e boa parte de F4 não dependem delas; desenvolvimento e teste usam respx e dublê. Obter a chave é pré-requisito só da validação de F2 |
| Proxy corporativo bloqueando `*.atlassian.net` ou `*.freshservice.com` | F2 não valida na máquina da empresa | R-007 torna o bloqueio diagnosticável; validar via rede alternativa, como já foi feito no `data-receiver` |
| Enum de 13 squads derruba a acurácia do LLM abaixo de 80% | LLM permanece desligado | Resultado aceitável: o determinístico cobre o caso principal porque a squad vem preenchida na origem. O golden set decide, como manda o princípio I |
| Campo `Squad` vazio em parte dos chamados do sandbox | Mais itens em revisão humana do que o esperado | Medir a taxa antes de F2 fechar; é justamente o número que justifica o fallback por LLM |
