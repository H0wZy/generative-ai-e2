# Quickstart — validação da Plataforma Unificada ITSM + Agile

Roteiro de validação. Cada cenário prova um requisito e nomeia o que observar. Não contém código de implementação — isso é `tasks.md`.

## Pré-requisitos

```bash
make install          # deps do backend (.venv) e do frontend (npm)
make install-rag      # sentence-transformers + torch CPU, ~750 MB — só para o assistente
make dev              # postgres + api + migrations + frontend (porta 3000)
make rag-sync         # indexa docs/**/*.md em rag/data/knowledge.db
```

`backend/.env` — o que esta feature acrescenta:

```bash
JIRA_BOARD_ID=42                       # numérico; ver "Descobrir o board" abaixo
RAG_SEARCH_URL=http://rag-search:8100  # http://localhost:8100 fora do compose

ASSISTANT_ENABLED=false                # true só depois do golden set (cenário 12)
ASSISTANT_BASE_URL=https://openrouter.ai/api/v1
ASSISTANT_MODEL=nvidia/nemotron-3-ultra-550b-a55b:free
ASSISTANT_TIMEOUT_SECONDS=60
ASSISTANT_MAX_CONTEXT_CHARS=12000
OPENROUTER_API_KEY=...                 # secret — nunca commitar
```

### Descobrir o board

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/agile/1.0/board?projectKeyOrId=$JIRA_PROJECT_KEY" \
  | python -m json.tool
```

Anotar `values[].id` e conferir `values[].type` (`scrum` ou `kanban`). Confirmar que o board expõe estimativa e limites de coluna:

```bash
curl -s -u "$JIRA_EMAIL:$JIRA_API_TOKEN" \
  "$JIRA_BASE_URL/rest/agile/1.0/board/$JIRA_BOARD_ID/configuration" \
  | python -m json.tool
```

Verificar `estimation.field.fieldId` presente (senão os pontos vêm `null` em toda parte) e `columnConfig.constraintType` diferente de `none` se quiser exercitar FR-028.

---

## Cenários

### 1 — Shell, workspaces e tema (US1, FR-001 a FR-005)

Abrir `http://localhost:3000`.

- KPIs de ITSM e de Agile na mesma tela, cada um com rótulo e janela de tempo.
- Acionar **Agile** no seletor: a sidebar troca para Home, Dashboard, Backlog, Scrum, Kanban, Reports, Assistente, Administração. A URL vira `/agile`. **Sem recarga de página** — verificar na aba Network que não houve navegação de documento.
- Acionar o alternador de tema, recarregar: o tema escolhido persiste.
- Percorrer a sidebar inteira só com `Tab`: foco visível em todo item, `Enter` navega.

### 2 — Placeholders nomeados (FR-004)

Acionar **Assets**. A página diz "Assets — em construção", com o nome da seção. Não é 404, não é link morto. Repetir para Base de Conhecimento, Automações e Administração.

### 3 — Fila de tickets (US2, FR-014 a FR-016)

```bash
make ingest-demo && make worker-once
```

Abrir `/itsm`.

- Cada linha traz identificador, assunto, prioridade, status, responsável e SLA.
- Linhas em falha, retry e revisão humana têm destaque visual próprio.
- Filtrar por status e prioridade ao mesmo tempo, e buscar texto: o total exibido acompanha o recorte.
- Recarregar a página com os filtros aplicados: o recorte sobrevive (estão em `searchParams`).

### 4 — Detalhe e timeline (FR-017, FR-018, FR-021)

Abrir um ticket em falha.

- Solicitante, categoria, impacto, urgência, SLA, decisão de roteamento com grau de confiança.
- Timeline em ordem cronológica, com a causa de cada tentativa falha.
- **Verificar que nenhum evento da timeline exibe assunto ou descrição do ticket** — é a lista branca de `detail` (Princípio II).
- Voltar para a lista: os filtros de antes continuam aplicados.

### 5 — Reprocessamento (FR-019, FR-020)

No detalhe de um ticket `failed`, acionar reprocessar.

- O status muda na tela sem recarga manual.
- Acionar duas vezes rápido: o botão desabilita durante a requisição e a segunda chamada recebe `409` — uma única solicitação efetiva.
- Abrir um ticket `completed`: a ação não aparece e o motivo é dito.

### 6 — Agile sem Jira (FR-030, SC-008)

Comentar `JIRA_BASE_URL` em `backend/.env` e reiniciar a API.

- `/agile`, `/agile/backlog`, `/agile/scrum`, `/agile/kanban` mostram estado de indisponibilidade **nomeado**, com orientação de configuração.
- `/`, `/itsm` e `/reports` continuam funcionando normalmente. **Este é o cenário que prova SC-008** — rodar também desligando o Postgres e depois o serviço de RAG, um de cada vez.

### 7 — Dashboard de sprint (FR-022 a FR-025)

Restaurar as credenciais. Abrir `/agile`.

- Nome, objetivo, datas, dias restantes, pontos comprometidos e concluídos batem com o board no Jira.
- Burndown com linha ideal e real; dias futuros não desenhados.
- Bloqueios com título, motivo, responsável e dias parados.
- Velocidade dos últimos sprints fechados.

Board sem sprint ativo: estado vazio explicando, com acesso ao Backlog. Não é erro.

### 8 — Backlog e quadros (FR-026 a FR-028)

`/agile/backlog`: ordem idêntica à do backlog no Jira, épico e progresso por épico.

`/agile/scrum` e `/agile/kanban`: as colunas são as do board, não um conjunto fixo. Renomear uma coluna no Jira e recarregar após 60 s (TTL do cache) — o nome novo aparece.

FR-028: definir `max` numa coluna do Jira e colocar mais cards que o limite. A coluna sinaliza o estouro.

### 9 — Transição com escrita real (FR-046 a FR-048, SC-013)

Arrastar um card de "To Do" para "In Progress".

- O card muda de coluna de imediato.
- **Conferir no Jira** que o status mudou — em até 3 segundos (SC-013).
- O status exibido é o que o Jira devolveu, não o esperado.

Caminho de recusa: arrastar de "To Do" direto para uma coluna que o workflow não alcança.

- O card **volta** à coluna de origem.
- A mensagem nomeia as transições disponíveis a partir do status atual — não é erro genérico.

Acessibilidade: repetir a mesma transição pelo menu "Mover para", só com teclado.

### 10 — Reports (FR-032 a FR-035)

Acionar **Reports** a partir de ITSM e a partir de Agile: abre dentro do shell nos dois casos, com sidebar, tema e seletor preservados.

Base vazia ⇒ fluxo de ingestão em vez de gráficos vazios. Carregar planilha (`make analytics-load` ou o upload da tela), ajustar filtros e periodicidade: throughput, distribuição, lead time e cobertura recalculam. Recorte sem resultado ⇒ vazio explícito em cada visualização, não gráfico em branco.

### 11 — Serviço de busca do RAG

```bash
curl -s localhost:8100/health
curl -s -X POST localhost:8100/search \
  -H 'content-type: application/json' \
  -d '{"query":"idempotência do worker","limit":5}' | python -m json.tool
```

`results` com `file_path`, `heading_path`, linhas e `distance`. Pergunta fora de domínio ("como fazer bolo de cenoura") ⇒ `results: []`, `total: 0`, **200** — não é erro.

### 12 — Assistente (FR-036 a FR-045)

**Antes de `ASSISTANT_ENABLED=true`**: rodar o golden set do assistente e publicar o número. É a condição do Princípio I registrada em research.md R5. Sem isso, `/assistant` responde `disabled` — o que também é um caminho a validar.

Com o assistente ativo, em `/assistant`:

| Verificar | Requisito |
|---|---|
| Pergunta sobre a arquitetura devolve resposta **e** fontes; cada fonte abre o trecho com origem | FR-036, FR-037 |
| Pergunta fora de domínio devolve `no_grounding` — declara falta de fundamento, não inventa | FR-038 |
| Pergunta de acompanhamento é interpretada no contexto da anterior | FR-039 |
| Histórico longo devolve `truncated_history: true` e a tela avisa | FR-044 |

Modos de falha — forçar cada um e conferir que a mensagem os distingue **e que as fontes aparecem mesmo assim** (FR-043):

```bash
# indisponível
ASSISTANT_BASE_URL=http://127.0.0.1:9   # porta fechada
# tempo excedido
ASSISTANT_TIMEOUT_SECONDS=1
# limite de uso: repetir perguntas até o tier free devolver 429
```

Segurança (FR-040, FR-042):

- Inspecionar o tráfego do navegador: **nenhuma** resposta carrega `OPENROUTER_API_KEY`, credencial de Jira, URL do provedor ou nome do modelo.
- Inspecionar `docker compose logs api` após uma pergunta: nenhum token, nenhum conteúdo de ticket.
- `pytest backend/tests/test_redaction.py` — e-mail, telefone e CPF substituídos por marcador.

### 13 — Acessibilidade e responsividade (FR-008, FR-009, SC-005, SC-006)

Em **cada** rota implementada, nos **dois** temas:

- Verificação automatizada sem violação de nível A ou AA.
- Viewport a 360 px: nenhuma rolagem horizontal na página. Tabela e quadro rolam dentro do próprio contêiner.
- Preferência de movimento reduzido ativa: transições suprimidas.
- Contraste ≥ 4.5:1 para texto, ≥ 3:1 para elemento gráfico. **Conferir explicitamente o item inativo da sidebar no tema claro** — é o par que o protótipo reprovava (research.md R9).

### 14 — Suíte sem credencial e sem rede (Princípio IV)

```bash
env -u JIRA_BASE_URL -u JIRA_API_TOKEN -u OPENROUTER_API_KEY make test
make rag-test
```

Ambas verdes. Qualquer falha aqui significa que um teste está alcançando a rede — corrigir o teste, não a configuração.

---

## Definição de pronto

- [X] Cenários 1 a 14 executados com evidência registrada em `evidence/evaluations/2026-07-29-plataforma-unificada-itsm-agile.md`
- [X] `make test` (245) e `make rag-test` (51) verdes sem credencial e sem rede
- [X] ADR do uso de LLM remoto registrado em `docs/ai/ai-decisions.md` (ADR-012)
- [X] Golden set do assistente executado com número publicado — `recall@5 = 0,72` (18 perguntas)
- [X] `frontend/src/app/analytics/` movido com `git mv` para `reports/`; nenhuma referência restante
- [X] Seção "o que ficou de fora" do README atualizada — SLA sem prazo, avatar sem imagem, Agile dependente de credencial viva, board vazio, assistente desligado
