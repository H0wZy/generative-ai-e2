# Validação — Plataforma Unificada ITSM + Agile

**Data:** 2026-07-29
**Spec:** `specs/002-unified-itsm-agile-ui/` (quickstart.md, 14 cenários)
**Ambiente:** backend em container (`docker compose`, imagem reconstruída), Postgres local, frontend `next start` na porta 3100, serviço de busca do RAG em `127.0.0.1:8100`, Jira Cloud real (board `2` — `FRESH board`).

Tudo abaixo é resultado **medido**, não esperado. Onde a medição contrariou o desenho, o desenho mudou e está anotado.

---

## 1 — Shell, workspaces e tema (FR-001 a FR-005)

| Verificação | Resultado |
|---|---|
| Sidebar ITSM | Home, Dashboard, Assets, Base de Conhecimento, Reports, Automações, Assistente de IA, Administração |
| Sidebar Agile | Home, Dashboard, Backlog, Quadro Scrum, Quadro Kanban, Reports, Assistente de IA, Administração |
| Troca de workspace | `/itsm` → `/agile`, `performance.getEntriesByType('navigation').length` **permanece 1** — navegação do App Router, sem recarga de documento (SC-003) |
| Item ativo | `aria-current="page"` no item correspondente à rota |
| Tema | Alternador escreve `data-theme` e `localStorage`; após `location.reload()` o tema escolhido (`light`) persiste |
| Teclado | 12 elementos focáveis na rota, todos com `tabIndex >= 0` |

## 2 — Placeholders nomeados (FR-004)

`/em-construcao/assets`, `/base-de-conhecimento`, `/automacoes`, `/administracao` respondem **200** com o nome da seção no `<h2>` e o texto "Seção em construção". Nenhum 404, nenhum link inerte.

## 3 — Fila de tickets (FR-014 a FR-016)

Base carregada com `make ingest-demo && make worker-once`.

```
total: 5
FS-OTHER-4001  needs_human_review  prio: low     reprocessável: True
FS-100         completed           prio: high    reprocessável: False
FS-PROD-1001   completed           prio: urgent  reprocessável: False
FS-AUTH-3001   completed           prio: high    reprocessável: False
```

| Recorte | Resposta |
|---|---|
| `?status=needs_human_review` | 200, `total=1` |
| `?priority=high` | 200, `total=3` |
| `?q=FS` | 200, `total=5` |
| `?limit=1&offset=1` | 200, `total=5` (total é do recorte, não da página) |
| `?q=` com 121 caracteres | **422** |

## 4 — Detalhe e timeline (FR-017, FR-018, FR-021)

- Timeline em ordem cronológica ascendente: **confirmado**.
- Eventos e chaves liberadas pela lista branca:

```
Ticket recebido               -> ['source_ticket_id', 'event_id']
Enviado para revisão humana   -> ['reason']
Reprocessamento solicitado    -> []
Enviado para revisão humana   -> ['reason']
```

- **Assunto e descrição do ticket não aparecem em nenhum `detail`** — verificado por comparação direta contra os valores reais do ticket (Princípio II).

## 5 — Reprocessamento (FR-019, FR-020)

| Chamada | Resposta |
|---|---|
| 1ª em ticket `needs_human_review` | **200**, `reprocessed: true`, status vai a `pending` |
| 2ª imediata no mesmo ticket | **409**, `reason: "not_eligible"` — uma única solicitação efetiva |
| Ticket `completed` | **409**, `reason: "already_linked"`, `jira_issue_key: SQD-123` |
| `workflow_execution_id` inexistente | **404** |

## 6 — Indisponibilidade e isolamento de falha (FR-030, SC-008)

API subida **sem** credencial de Jira (porta 8001), frontend apontado para ela (porta 3101).

| Rota | Resposta |
|---|---|
| `/api/v1/agile/sprint` | **200** `available:false` `reason:"not_configured"` `detail:"JIRA_BOARD_ID não configurado"` |
| `/api/v1/agile/backlog` | idem |
| `/api/v1/agile/board?scope=sprint` | idem |
| `/api/v1/metrics`, `/api/v1/workflows`, `/health` | **200** — ITSM não é afetado |

Na tela, `/agile`, `/agile/backlog`, `/agile/scrum` e `/agile/kanban` renderizam o estado nomeado "Integração com o Jira não configurada" **com a orientação de configuração** (cita `JIRA_BOARD_ID`). `/`, `/itsm`, `/reports` e `/assistant` seguem com o shell íntegro e sem `error.tsx` acionado. **SC-008 comprovado.**

## 7 e 8 — Sprint, backlog e quadros contra o Jira real

```
board:    {'board_id': 2, 'name': 'FRESH board'}
sprint:   FRESH Sprint 1 | goal: None | days_left: 12 | 0.0 / 0.0 pontos
velocity: 0 séries        blocked: 0
burndown: 15 dias, ideal 0.0 -> 0.0, actual [0.0, 0.0, 0.0, None, ...]
backlog:  10 itens em ordem de rank, 1 épico (FRESH-100)
board:    A fazer 9 | Fazendo 1 | Em análise 1 | Feito 1  (constraint_type: none)
```

O board expõe os dados; o que está vazio é o board, não o código:

- `goal` chega como string vazia do Jira e é normalizado para `None` — a tela mostra "Sem objetivo definido no Jira".
- `customfield_10016` é solicitado e **retornado** pelo Jira (confirmado por chamada direta: campo presente, valor `null` em todas as issues). Nenhuma issue está estimada, então os pontos são `null` por dado, não por bug.
- Nenhum sprint encerrado ⇒ velocidade cai em estado vazio nomeado, não gráfico em branco.
- `constraintType: "none"` e nenhuma coluna com `max` ⇒ `over_wip` nunca acende. FR-028 não tem o que exibir neste board.

**Correção que esta validação provocou:** a lista de campos pedida ao Jira era constante e **não incluía o campo de estimativa**, então os pontos viriam `null` mesmo num board estimado. O campo passou a ser anexado em tempo de chamada, a partir de `estimation.field.fieldId` da configuração do board.

## 9 — Transição com escrita real (FR-046 a FR-048, SC-013)

Sequência executada contra o Jira real, com o board restaurado ao estado inicial ao fim.

| Ação | Resposta |
|---|---|
| Destino igual ao status atual (`FRESH-2` em "Em análise" → "Em análise") | **200** `applied:false` `reason:"already_there"` — **nenhuma chamada ao Jira** |
| Coluna inexistente ("Coluna Fantasma") | **409** `reason:"no_transition"`, `available_transitions: ["A fazer","Fazendo","Em análise","Feito"]` |
| `FRESH-2` → "Fazendo" | **200** `applied:true` `new_status_name:"Fazendo"` (relido do Jira) |
| `FRESH-2` → "Em análise" (volta) | **200** `applied:true` `new_status_name:"Em análise"` |

Estado do board antes e depois da bateria: **idêntico**.

A guarda de `already_there` é necessária porque o Jira **oferece** transição para o próprio status atual (medido em research.md R12b) — a ausência da transição não serviria de guarda.

## 10 — Reports dentro do shell (FR-032 a FR-035)

`/reports` responde 200 com o shell completo (sidebar, tema, seletor de workspace) tanto a partir de ITSM quanto de Agile. `frontend/src/app/analytics/` foi movido com `git mv` e não existe mais no disco; nenhuma referência a `/analytics` restou no código. Cada aba sem dado renderiza estado vazio nomeado por visualização.

## 11 — Serviço de busca do RAG

```
GET  /health  -> 200 {"status":"ok","indexed_chunks":110}
POST /search  {"query":""}                          -> 422
POST /search  {"query":"como fazer um bolo de cenoura"} -> 200 total=0 results=[]
POST /search  {"query":"chave de idempotência para evitar issues Jira duplicadas"}
              -> 200 total=5, melhor distância 0.411 (operational-contract.md)
```

`content` volta **cru**, sem `<untrusted_document>` — confirmado. A marcação é aplicada pelo backend ao montar o prompt, não no transporte.

**Achado:** a consulta curta `"idempotência do worker"` devolve `total: 0` porque a melhor distância é **0.507**, acima do limiar calibrado de 0.50. A biblioteca (`rag.search.query.search`) devolve a mesma lista vazia — serviço e biblioteca concordam. É o limiar funcionando, não falha: consulta curta demais não tem sinal suficiente. O exemplo do quickstart era otimista.

## 12 — Assistente (FR-036 a FR-045)

`ASSISTANT_ENABLED=false` (padrão). `POST /assistant/ask` responde **200** com `status: "disabled"`, `answer: null`, `sources: []` — sem tocar no RAG nem no provedor. `question` vazia ou acima de 2000 caracteres ⇒ **422**.

**Golden set do assistente executado (portão do Princípio I):** conjunto ampliado de 12 para 18 perguntas, seis delas do domínio do assistente.

```
recall@5 = 13/18 = 0,72   (max_distance = 0,50)
```

Cinco falhas de recuperação, nomeadas no ADR-012. **O número não foi ajustado** — nenhum limiar afrouxado, nenhuma pergunta reescrita para inflar. Registrado em `docs/ai/ai-decisions.md` (ADR-012) junto com o que sai da máquina, a redação de PII aplicada antes e a retenção de prompt pelo provedor no nível gratuito.

Cobertura por teste (`backend/tests/test_assistant.py`, 15 casos): recuperação vazia devolve `no_grounding` **sem chamar o cliente do modelo**; cada modo de falha (`rate_limited`, `unavailable`, `timeout`) devolve status próprio **com `sources` preenchido**; nenhuma resposta carrega chave, nome de modelo ou URL do provedor.

## 13 — Acessibilidade e responsividade (FR-008, FR-009, SC-005, SC-006)

Verificação com estilo computado real no navegador, **nos dois temas**, em `/`, `/itsm`, `/agile`, `/agile/backlog`, `/agile/scrum`, `/agile/kanban`, `/reports`, `/assistant` e `/em-construcao/[secao]`.

**Contraste: zero violação AA em ambos os temas** após três correções que a medição encontrou:

| Achado medido | Correção |
|---|---|
| `neutral-600` como texto secundário: 4,31:1 sobre branco e 3,52:1 sobre a superfície escura | Token semântico `--color-muted`, que vira com o tema (neutral-500 no escuro, neutral-700 no claro) |
| `accent-400` como link/foco: **1,86:1** sobre o fundo claro | Tokens `--color-link` e `--color-focus`, accent-300 no escuro e accent-700 no claro |
| `hover:bg-neutral-900` no item de sidebar: fundo escuro sob texto escuro no tema claro, **2,67:1** | Token `--color-elevated` (neutral-900 no escuro, neutral-200 no claro) |
| Selo "em breve" no item **ativo**: **1,57:1** no tema claro (fundo roxo escuro + texto muted escuro) | Selo herda a cor do item quando ativo |

Também corrigidos: alvo de toque de 20 px na marca da sidebar (agora `min-h-9`) e campo de busca sem nome acessível explícito (`aria-label` adicionado).

**Nota de método:** a primeira rodada acusou dezenas de falsos positivos. `transition-colors` interpola a cor por 150 ms, e a medição feita logo após a troca de tema lia a cor **no meio da transição**. A auditoria só é válida com as transições suprimidas — foi assim que os quatro achados reais acima foram isolados.

**Viewport de 360 px:** `scrollWidth - clientWidth = 0` em **todas** as nove rotas. Tabela e quadro rolam dentro do próprio contêiner.

**Movimento reduzido:** `@media (prefers-reduced-motion: reduce)` em `globals.css` zera duração de animação e de transição em todo o app.

## 14 — Suíte sem credencial e sem rede (Princípio IV)

```
env -u JIRA_BASE_URL -u JIRA_EMAIL -u JIRA_API_TOKEN -u OPENROUTER_API_KEY pytest
  -> 245 passed

pytest rag/tests
  -> 51 passed
```

## Auditoria de log e tráfego (FR-042, SC-010)

`docker compose logs api` após a bateria de transições e as perguntas ao assistente — 82 linhas:

| Procurado | Ocorrências |
|---|---|
| Valor de `JIRA_API_TOKEN` | 0 |
| Valor de `JIRA_EMAIL` | 0 |
| Valor de `OPENROUTER_API_KEY` | 0 |
| `Authorization`, `Basic <base64>`, `Bearer `, `ATATT`, `sk-or-` | 0 |
| Assunto/descrição de ticket, `untrusted_document` | 0 |

---

## Correções de código provocadas por esta validação

1. **Campo de estimativa não era pedido ao Jira** — pontos viriam `null` mesmo num board estimado. Corrigido (cenário 8).
2. **Quatro pares de cor reprovando AA no tema claro** — a rampa Nocturne não vira com o tema; tokens semânticos resolvem (cenário 13).
3. **`conftest.py` redeclarava as rotas** em vez de usar o router de produção. Os filtros novos de `/workflows` passavam nos testes sem estar montados na aplicação real. A fixture passou a montar `create_router` e sobrescrever só a dependência do cliente Jira — a suíte agora exercita o que de fato é servido.
4. **`docker compose` não repassava `backend/.env` ao container** — a API rodava sem `JIRA_BOARD_ID` e toda rota de Agile respondia `not_configured` na aplicação real, embora os testes passassem. Adicionado `env_file` com `required: false`.
5. **`depends_on: rag-search` na API** obrigaria a construir uma imagem de vários GB (torch + modelo de embedding) só para subir o backend. Removido: busca indisponível vira `no_grounding`, não falha de boot.

## Correções da revisão de código (mesma data, após os 14 cenários)

6. **`scope_added_points` estava fixo em `0.0`.** O card "Escopo adicionado" do dashboard mostraria zero em qualquer board, e `committed_points` somava o escopo adicionado junto com a linha de base — os dois números que o contrato pede separados eram um só. O cálculo já existia dentro do burndown; foi extraído para `entry_days()` e passou a alimentar também o resumo do sprint. `committed = total - scope_added`.
7. **Cache TTL crescia sem teto.** A chave do backlog carrega `offset`, que vem do cliente, e o dicionário só encolhia quando a **mesma** chave era relida — o que nunca acontece para um offset arbitrário. Numa API sem autenticação isso é caminho de exaustão de memória, não hipótese. `set()` agora varre o que expirou antes de inserir.
8. **Serviço de busca fora do ar virava `no_grounding`.** O cliente engolia falha de conexão e devolvia lista vazia, indistinguível de "nada relevante encontrado" — a tela afirmaria "a documentação indexada não tem trecho suficiente" quando o que houve foi falha de infraestrutura. `RagSearchClient` agora levanta `RagUnavailable` e o serviço mapeia para `status: "unavailable"`. Contrato atualizado.

Suíte após as correções: **249 passed** (245 + 4 casos novos cobrindo exatamente os três achados).

## Pendências conhecidas

- **T037a — povoar o board FRESH no Jira.** Estimar issues em `customfield_10016`, vincular épicos, escrever objetivo do sprint, encerrar ao menos dois sprints e definir `max` numa coluna. Sem isso, sprint, burndown, velocidade e limite de WIP renderizam estados vazios corretos, porém vazios. **É trabalho de dado, não de código.**
- **`ASSISTANT_ENABLED` segue `false`.** O número está publicado (0,72); ligar é decisão de quem opera, ciente de que o nível gratuito do provedor pode reter prompt.
