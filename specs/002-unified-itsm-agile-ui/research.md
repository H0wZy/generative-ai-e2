# Research — Plataforma Unificada ITSM + Agile

**Date**: 2026-07-28 | **Plan**: [plan.md](./plan.md)

Cada item resolve uma incógnita que o desenho da Fase 1 depende. Fontes verificadas em 2026-07-28 contra a documentação oficial e contra o código real do repositório.

---

## R1 — Colunas, limite de WIP e campo de estimativa do board Jira

**Decision**: Ler tudo de `GET /rest/agile/1.0/board/{boardId}/configuration`. Nada de campo de story points configurado por variável de ambiente.

**Rationale**: A resposta entrega, numa única chamada, exatamente o que FR-027, FR-028 e FR-022 precisam:

```json
{
  "columnConfig": {
    "columns": [
      { "name": "To Do", "statuses": [{ "id": "1" }, { "id": "4" }] },
      { "name": "In progress", "min": 2, "max": 4, "statuses": [{ "id": "3" }] },
      { "name": "Done", "statuses": [{ "id": "5" }] }
    ],
    "constraintType": "issueCount"
  },
  "estimation": { "type": "field", "field": { "fieldId": "customfield_10002", "displayName": "Story Points" } },
  "ranking": { "rankCustomFieldId": 10020 }
}
```

- `columnConfig.columns[]` na ordem do board → FR-027, colunas reais em vez de conjunto fixo.
- `max`/`min` + `constraintType` (`none` | `issueCount` | `issueCountExclSubs`) → FR-028. `constraintType: "none"` significa sem limite; a coluna não sinaliza estouro.
- `estimation.field.fieldId` → o ID do campo de story points **descoberto em tempo de execução**, resolvendo a variação por instância sem adivinhação.
- A documentação afirma que a última coluna com status mapeado é tratada como "Done". Usar isso para calcular pontos concluídos, em vez de casar o nome da coluna com a string "Done".

**Alternatives considered**:
- `JIRA_STORY_POINTS_FIELD` por variável de ambiente — rejeitado: o board já declara o campo, e configurar à mão erra em silêncio quando o valor não bate.
- Casar nome de coluna por string ("Done", "Concluído") — rejeitado: quebra em board em português ou renomeado.

---

## R2 — Sprint ativo, backlog e issues

**Decision**:
- `GET /rest/agile/1.0/board/{boardId}/sprint?state=active` — sprint corrente. Lista vazia = estado "sem sprint ativo" (US3 cenário 8).
- `GET /rest/agile/1.0/board/{boardId}/sprint?state=closed` — últimos N sprints fechados para a curva de velocidade.
- `GET /rest/agile/1.0/sprint/{sprintId}/issue` — issues do sprint, base do quadro Scrum, do burndown e dos bloqueios.
- `GET /rest/agile/1.0/board/{boardId}/backlog` — backlog na ordem de rank (FR-026).
- Quadro Kanban: issues do board via `GET /rest/agile/1.0/board/{boardId}/issue`, distribuídas pelas colunas de R1.

**Rationale**: Campos do sprint confirmados na documentação: `id`, `state`, `name`, `startDate`, `endDate`, `completeDate`, `goal`, `originBoardId` — cobrem FR-022 sem chamada extra. O backlog já vem ranqueado pelo endpoint, então FR-026 não precisa ordenar no cliente.

**Alternatives considered**:
- Variantes "enhanced" (`/backlog` e `/sprint/{id}/issue` enhanced) existem na documentação — não adotadas nesta feature: a paginação e o formato clássicos bastam para o volume de um board de demo, e o clássico tem superfície menor. Registrado como caminho de migração se o volume crescer.
- Endpoint interno de burndown do Greenhopper — rejeitado: não é API pública, quebra sem aviso.

---

## R3 — Burndown sem endpoint de burndown

**Decision**: Calcular no backend a partir das issues do sprint com `expand=changelog`.

- **Linha ideal**: reta de `pontos comprometidos` até `0`, um ponto por dia entre `startDate` e `endDate`.
- **Linha real**: para cada dia, `comprometido - soma dos pontos das issues que entraram em status de coluna "Done" até aquele dia`, lido do changelog do campo `status`.
- **Escopo adicionado**: issues cuja entrada no sprint (changelog do campo `Sprint`) é posterior a `startDate` elevam o comprometido a partir daquele dia — é o que faz o gráfico refletir o escopo sem distorcer a ideal (FR-023, edge case do spec).
- Dias futuros da linha real não são desenhados.

**Rationale**: O único caminho público e estável. O changelog é a fonte que o próprio Jira usa.

**Alternatives considered**: Snapshot diário persistido no Postgres — rejeitado por Princípio V (infraestrutura que o MVP não usa) e porque o changelog já é histórico completo.

**Risco conhecido**: `expand=changelog` engorda a resposta. Mitigado pelo cache TTL de 60 s (R7) e por buscar changelog apenas na rota do dashboard, não na do quadro.

---

## R4 — Transição de card com escrita real (FR-046, FR-047, FR-048)

**Decision**: Duas chamadas, nesta ordem.

1. `GET /rest/api/3/issue/{key}/transitions` — transições **disponíveis a partir do status atual**.
2. Casar o `to.id` de cada transição contra os `statuses[]` da coluna de destino (R1). Se houver correspondência, `POST /rest/api/3/issue/{key}/transitions` com `{"transition": {"id": "<id>"}}`.
3. Se não houver, responder `409` nomeando as transições disponíveis — é literalmente o que FR-047 pede.

**Rationale**: Workflow do Jira frequentemente não permite salto entre colunas não adjacentes. Descobrir a transição em vez de assumir um ID é a diferença entre "falhou" e "não dá para ir daqui para lá; daqui você pode ir para X ou Y".

O frontend aplica o movimento de imediato e reverte no erro (FR-048): o estado das colunas é `useState` no componente cliente do quadro, a reversão é restaurar o snapshot anterior.

**Alternatives considered**:
- `PUT /rest/api/3/issue/{key}` com `fields.status` — rejeitado: o Jira não permite alterar status por edição de campo, só por transição.
- Mapa fixo de transições por configuração — rejeitado: quebra a cada mudança de workflow no Jira.

**Nota de permissão**: o autor confirmou que a credencial em `backend/.env` tem permissão de transição. A resposta `403` continua tratada como indisponibilidade nomeada (FR-030), não como falha genérica.

---

## R5 — Assistente: recuperação determinística antes do modelo

**Decision**: Pipeline de três estágios, com o corte determinístico antes do LLM.

1. **Recuperar** — `POST` no serviço HTTP do RAG (R6), que chama `rag.search.query.search()` com o `max_distance=0.50` já calibrado.
2. **Cortar** — zero resultado abaixo do limiar ⇒ retorna `status: "no_grounding"` e **não chama o modelo**. É FR-038 resolvido por regra, não por instrução de prompt.
3. **Redigir** — trechos + histórico da sessão vão ao OpenRouter. Cada trecho entra envolto em `<untrusted_document>`, como `rag/mcp/server.py` já faz. A resposta é devolvida com a lista de fontes (arquivo, linhas, distância).

**Rationale**: Atende o Princípio I sem transformar o assistente em classificador. O limiar `0.50` não é arbitrário — `rag/search/query.py` documenta a medição: a menor distância de uma pergunta fora de domínio foi `0.5019`, e `0.45` derrubou recall@5 de 0.92 para 0.50. Reusar o número medido em vez de escolher outro.

**Alternatives considered**:
- Deixar o modelo decidir se tem fundamento — rejeitado: é exatamente a decisão que o Princípio I tira do modelo.
- Reranking antes do LLM — rejeitado por Princípio V; o golden set do RAG não mostra que faz falta.

**Condição de ativação**: golden set do assistente executado e número publicado, estendendo `rag/golden/`. Sem isso, `ASSISTANT_ENABLED` fica `false` — mesma disciplina que o README já aplica a `LLM_ENABLED`.

---

## R6 — Como o backend alcança a busca do RAG

**Decision**: Serviço HTTP mínimo em `rag/http/app.py`, um endpoint `POST /search`, container próprio no compose, consumido pelo backend via `httpx` com `RAG_SEARCH_URL`.

**Rationale**: O container da API hoje não tem nenhuma dependência de ML. Importar `rag` traria `sentence-transformers` + `torch`. O serviço HTTP reusa `rag.search.query` sem tocá-lo e mantém a independência que a constituição exige do RAG.

**Alternatives considered**:
- Import direto de `rag` no backend — rejeitado pelo peso do container e pelo acoplamento.
- Cliente MCP a partir do backend — rejeitado: `fastmcp` no backend mais gestão de subprocesso stdio para uma única chamada de função.
- Servir a busca pelo próprio processo do MCP — rejeitado: o MCP é stdio, não HTTP, e é consumido por agente, não por navegador.

**Consequência**: `fastapi` e `uvicorn` entram em `rag/requirements.txt`. Ambas já existem no backend, então nenhuma versão nova entra no repositório.

---

## R7 — Limite de requisição do Jira

**Decision**: Cache em processo, TTL de 60 s, chaveado por `(endpoint, board_id, params)`. Invalidado na escrita de transição (R4). Cerca de 15 linhas, sem dependência.

**Rationale**: Um carregamento de dashboard Agile faz 3-4 chamadas ao Jira. O avaliador vai navegar entre as quatro telas de Agile várias vezes durante a apresentação. 60 s é curto o bastante para o dado parecer vivo e longo o bastante para não bater no limite.

**Alternatives considered**: Redis rejeitado (Princípio V). `functools.lru_cache` rejeitado: não expira, e dado de sprint precisa envelhecer. Cache no `fetch` do Next rejeitado: o problema é o número de chamadas Jira→backend, não navegador→backend.

---

## R8 — Next.js 16: o que mudou em relação ao conhecido

**Decision**: App Router com Server Components por padrão; cliente apenas onde há interação.

Fatos verificados na documentação embarcada em `frontend/node_modules/next/dist/docs`:

- **`fetch` não é mais cacheado por padrão** e bloqueia a renderização até completar. O `cache: 'no-store'` espalhado pelo código atual virou redundante. Para não bloquear, envolver em `<Suspense>`; para cachear, a diretiva `use cache`.
- **`params` e `searchParams` são `Promise`** e precisam de `await`. Afeta `/itsm/[id]` e `/reports`.
- Convenções de arquivo disponíveis: `loading.js`, `error.js`, `not-found.js`, `template.js`, `default.js`, `route.js`, `proxy.js`.

**Aplicação**: cada seção ganha `loading.tsx` e `error.tsx` próprios — é o mecanismo do framework que satisfaz FR-007 sem código de estado escrito à mão.

**Componentes de cliente** (só estes): `theme-toggle`, `ticket-filters`, `board` (drag-and-drop e estado otimista), `reprocess-button` (já existe), `chat`. Todo o resto é servidor.

---

## R9 — Tokens Nocturne para Tailwind v4

**Decision**: Portar os tokens de `styles.css` do design system para `frontend/src/app/globals.css` como custom properties em `:root`, com sobrescrita em `:root[data-theme="light"]`, e expor ao Tailwind por `@theme inline`. As classes de componente do Nocturne (`.card`, `.tag`, `.btn`, `.table`) **não** são portadas — os equivalentes são componentes React usando os mesmos tokens.

**Rationale**: `@theme inline` é como o Tailwind v4 lê custom property, e o `globals.css` atual já usa esse padrão. Portar as classes CSS além dos tokens criaria dois sistemas de estilo concorrendo no mesmo arquivo.

Tokens portados: rampas `--color-neutral-100..900`, `--color-accent-100..900`, `--color-accent-2-100..900`, `--color-bg`, `--color-surface`, `--color-text`, `--color-divider`, escala `--space-1..8`, `--radius-sm|md|lg`, `--shadow-sm|md|lg`. Fonte Inter via `next/font/google`, substituindo Geist — o `@import` de Google Fonts do Nocturne **não** é copiado (`next/font` já resolve auto-hospedagem).

**Descartados**: `--color-section`, `--color-section-glow`, `--color-section-ghost` — o próprio design system os marca como "deck-scale fills only — not interface colors".

**Problema de acessibilidade encontrado, que precisa de correção**: o protótipo define o tema claro sobrescrevendo apenas `--color-bg`, `--color-surface`, `--color-text`, `--color-divider` e as sombras. As rampas neutra e de acento continuam as do tema escuro. Consequência concreta: item inativo da sidebar usa `--color-neutral-400` (`#b2b6ca`) sobre superfície clara (`#ffffff`) — razão de contraste ≈ **2.2:1**, reprova AA (mínimo 4.5:1) e derruba SC-005.

**Correção**: no tema claro, texto secundário e ícone inativo passam a usar `--color-neutral-600` (`#75798c`, ≈ 4.6:1 sobre branco) ou mais escuro. Todo par cor-de-texto/superfície é medido antes de entrar no `globals.css`, nos dois temas. Esta é uma divergência consciente do protótipo, exigida por FR-008, e deve ser registrada como tal.

---

## R10 — OpenRouter

**Decision**: Cliente `httpx` próprio contra `POST https://openrouter.ai/api/v1/chat/completions`, sem SDK.

**Rationale**: O esquema de requisição e resposta é o do Chat Completions da OpenAI, com pequenas diferenças. Uma função de ~30 linhas com `httpx`, que já é dependência do backend, cobre o caso. Adicionar o SDK da OpenAI para uma chamada viola o Princípio V.

Configuração (`Settings`, namespace separado do `llm_*` que o classificador de squad usa — os dois modelos coexistem e não devem compartilhar variável):

| Variável | Padrão |
|---|---|
| `ASSISTANT_ENABLED` | `false` |
| `ASSISTANT_BASE_URL` | `https://openrouter.ai/api/v1` |
| `ASSISTANT_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b:free` |
| `ASSISTANT_TIMEOUT_SECONDS` | `60` |
| `ASSISTANT_MAX_CONTEXT_CHARS` | `12000` |
| `OPENROUTER_API_KEY` | — (secret, já presente comentado em `.env.example`) |

**Tratamento de erro que FR-043 exige distinguir**: `429` ⇒ limite de uso; `5xx` e erro de conexão ⇒ indisponível; expiração do `timeout` ⇒ tempo excedido; corpo malformado ⇒ resposta inválida. Em todos, os trechos recuperados vão na resposta mesmo sem redação.

**Timeout de 60 s**: mais alto que os 20 s do `OllamaClient`. Modelo desse porte em tier gratuito responde na casa das dezenas de segundos sob carga; cortar em 20 s descartaria resposta válida.

**Alternatives considered**: SDK `openai` — rejeitado por Princípio V. Streaming de resposta — rejeitado nesta feature: exige rota de streaming e componente de cliente com leitor incremental, e o spec não pede resposta incremental.

---

## R11 — Remoção de PII antes do envio ao modelo (FR-040)

**Decision**: Função pura em `backend/app/services/redaction.py`, aplicada a todo texto de ticket antes de compor o prompt, com teste unitário próprio.

Remove por padrão: endereço de e-mail, telefone, CPF, e o nome do solicitante quando presente em campo estruturado. Substitui por marcador estável (`[email]`, `[telefone]`, `[documento]`, `[solicitante]`) para não destruir a legibilidade da frase.

**Rationale**: Documentação do OpenRouter e prática do setor indicam que endpoints gratuitos podem reter prompt para treino do provedor. Como o assunto e a descrição do ticket vêm do Freshservice sem controle de conteúdo, a remoção é a única barreira antes de o dado sair da máquina.

Ser função pura, e não filtro no cliente HTTP, permite testá-la sem rede — exigência do Princípio IV.

**Alternatives considered**: Confiar em política de privacidade do provedor — rejeitado. Bloquear o assistente sobre dados de ticket e permitir só perguntas de arquitetura — rejeitado pelo autor.

---

## R12b — O que o board real respondeu (medido em 2026-07-28)

Todas as suposições de R1–R4 foram exercitadas contra `tcsgen.atlassian.net`, board **2** (`FRESH board`, `type: simple` — team-managed). O que confirmou, o que mudou.

### Confirmado

- `GET /board/2/configuration` funciona em board team-managed. Colunas: `A fazer` (10004), `Fazendo` (10005), `Em análise` (10006), `Feito` (10007).
- `estimation.field.fieldId = customfield_10016` ("Story point estimate"). **R1 se sustenta** — o campo é descoberto, não configurado.
- `ranking.rankCustomFieldId = 10019`.
- Sprint ativo existe: `id=2`, `FRESH Sprint 1`, `2026-07-27` a `2026-08-10`. **R2 se sustenta.**
- `expand=changelog` retorna histórico. **R3 é viável.**
- Colunas em português confirmam a decisão de R1 de derivar "Done" da última coluna mapeada em vez de casar a string `"Done"`.

### Mudou o desenho

**1. O Jira oferece transição para o status atual.** `GET /rest/api/3/issue/FRESH-2/transitions`, com a issue em "Em análise", devolve as quatro colunas — inclusive `id=31 -> "Em análise"`. O desenho anterior assumia que o Jira omitiria essa transição e que a ausência serviria de guarda de idempotência. **Não serve.** A comparação `destino == atual` passa a ser do servidor, antes de qualquer chamada, devolvendo `already_there`.

**2. `goal` vem como string vazia**, não `null`. Tratar `""` como ausência de objetivo.

### Limitações do board atual, que não são defeito de código

| Achado | Consequência |
|---|---|
| `constraintType: "none"`, nenhuma coluna com `max` | **FR-028 não tem o que exibir.** O código trata (`over_wip` sempre `false`); exercitar o requisito exige definir um limite de coluna no Jira |
| Workflow team-managed alcança todas as colunas a partir de qualquer status | **FR-047 (`no_transition`) não dispara neste board.** O caminho existe e é testado pelo fake, mas não é demonstrável contra este Jira |
| Sprint ativo com 1 issue, `0` pontos somados, nenhum épico vinculado, `goal` vazio | Dashboard, burndown e backlog renderizam quase vazios |
| Nenhum sprint `closed` (só 1 `future` e 1 `active`) | **Gráfico de velocidade fica vazio** — FR-025 não tem histórico para mostrar |
| Backlog com 10 itens, board com 12 issues | Backlog é a única tela de Agile com volume real hoje |

**Ação necessária antes da apresentação, não antes do código**: povoar o board — estimar as issues em `customfield_10016`, vincular a épicos, escrever o objetivo do sprint, e fechar ao menos dois sprints para a velocidade ter série. É trabalho de dado no Jira, e está listado como task própria.

---

## R12 — Testes verdes sem credencial e sem rede

**Decision**: Um fake por integração nova, no molde do `FakeJiraClient` e do `FakeLLMClient` já existentes.

| Fake | Substitui | Comportamento |
|---|---|---|
| `FakeJiraAgileClient` | leitura de board/sprint/backlog e transições | Devolve fixture determinística; modo de erro configurável para exercitar FR-030 e FR-047 |
| `FakeAssistantClient` | OpenRouter | Resposta fixa; modos `rate_limited`, `unavailable`, `timeout` para exercitar FR-043 |
| `FakeRagSearchClient` | serviço HTTP do RAG | Trechos fixos, e lista vazia para exercitar o caminho `no_grounding` de FR-038 |

**Rationale**: `backend/tests/conftest.py` já monta um router com fakes. Os novos seguem o mesmo padrão — nenhuma infraestrutura de teste nova.

**Seleção em tempo de execução**: pelo mesmo padrão de `get_jira_client()` em `routes.py` — credencial configurada usa o cliente real, ausente usa o fake. Assim a aplicação sobe e navega sem nenhuma credencial, que é o que faz FR-030 e FR-043 testáveis à mão.
