# Implementation Plan: Plataforma Unificada ITSM + Agile

**Branch**: `002-unified-itsm-agile-ui` | **Date**: 2026-07-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-unified-itsm-agile-ui/spec.md`

## Summary

Substituir as duas telas soltas do frontend por um shell único com dois workspaces (ITSM e Agile), derivado do protótipo Nocturne aprovado, e ligar cada tela a dado real.

Três frentes, em ordem de dependência:

1. **Frontend** — reescrever `frontend/src/app` como App Router com layout de shell, tokens Nocturne portados para CSS custom properties consumidas pelo Tailwind v4, e componentes de gráfico em SVG inline. Zero dependência nova: sem biblioteca de gráfico, sem biblioteca de drag-and-drop, sem biblioteca de componentes.
2. **Backend** — estender `JiraClient` de escrita-apenas para leitura de board, sprint, backlog e transições; adicionar `GET /workflows/{id}` com timeline (hoje não existe); adicionar `POST /assistant/ask`.
3. **RAG** — expor a busca existente (`rag/search/query.py`) por um serviço HTTP mínimo, para que o backend a consuma sem herdar `sentence-transformers`/`torch` no seu próprio container.

O workspace é segmento de URL, não estado de cliente: `/itsm/*` e `/agile/*`. O seletor é um link. Nenhum gerenciador de estado entra no projeto.

## Technical Context

**Language/Version**: Python 3.11+ (backend, rag) · TypeScript 5 / React 19.2 (frontend)

**Primary Dependencies**: FastAPI, SQLAlchemy 2, httpx, pydantic-settings (backend, todas já instaladas) · Next.js 16.2 App Router, Tailwind CSS v4 (frontend, já instaladas) · sqlite-vec, sentence-transformers (rag, já instaladas) · **novas**: `fastapi` + `uvicorn` em `rag/requirements.txt` — ver Complexity Tracking

**Storage**: PostgreSQL (operacional, inalterado) · SQLite + sqlite-vec (RAG, inalterado) · nenhuma migration nesta feature

**Testing**: pytest (backend, rag) — suíte verde sem credencial e sem rede, via fakes · verificação de acessibilidade automatizada no frontend

**Target Platform**: Navegador moderno (last 2 versions) · Linux server para API

**Project Type**: Web application — `backend/` + `frontend/` + `rag/` já existentes

**Performance Goals**: Home utilizável em ≤2 s (SC-007) · transição de card refletida em ≤3 s (SC-013) · troca de workspace <1 s percebido (SC-003)

**Constraints**: Jira Cloud impõe limite de requisição por tenant — cache TTL no backend, não no navegador · OpenRouter free limita ~20 req/min e latência alta · nenhuma credencial pode chegar ao cliente (FR-031, FR-042) · sem autenticação nesta feature

**Scale/Scope**: ~13 rotas de frontend, 6 endpoints novos de backend, 1 endpoint novo de RAG, 1 usuário simultâneo (demo)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Situação | Como o desenho atende |
|---|---|---|
| **I. Determinismo primeiro, LLM como fallback medido** | ⚠️ Passa com condição | A recuperação é determinística: `rag.search.query` com `max_distance=0.50` já calibrado decide **antes** do modelo. Zero trecho acima do limiar = recusa determinística (FR-038), o LLM nem é chamado. O LLM só redige sobre trecho já recuperado, nunca decide roteamento, vínculo ou idempotência. **Condição**: ativação exige golden set do assistente executado com número publicado, estendendo `rag/golden/`. |
| **II. Entrada externa é não confiável** | ⚠️ Passa com desvio declarado | Trecho recuperado e conteúdo de ticket entram em bloco `<untrusted_document>`, como `rag/mcp/server.py` já faz. **Desvio**: a saída do assistente é texto livre, não enum fechado. Mitigação: a resposta é só exibida, nunca vira ação, escrita ou parâmetro de chamada. Nenhum conteúdo de ticket entra em log ou mensagem de erro. O README já registra taxa de sucesso 2/2 em injeção no classificador de squad — o assistente herda o mesmo tratamento, não o mesmo risco de decisão. |
| **III. Idempotência e rastreabilidade** | ✅ Passa | Nenhuma escrita nova no Postgres. A transição de card é idempotente por natureza do Jira: transicionar para o status atual não é oferecido e é rejeitado. Toda chamada a Jira e a OpenRouter registra `correlation_id`, duração e resultado — sem payload. |
| **IV. Segredo nunca entra no repositório** | ✅ Passa, com gate de teste | `JIRA_*` e `OPENROUTER_API_KEY` só em `.env`; `.env.example` já tem placeholder comentado para ambos. Todo dado de Jira e do assistente é servido pela API — o navegador nunca vê credencial (FR-031, FR-042). **Gate**: `FakeJiraAgileClient`, `FakeAssistantClient` e `FakeRagSearchClient` obrigatórios, no molde do `FakeJiraClient`/`FakeLLMClient` existentes, para a suíte rodar verde sem rede. |
| **V. Simples agora, escalável pelas costuras** | ✅ Passa | Zero dependência nova no frontend: gráficos em SVG inline (como o protótipo já faz), drag-and-drop nativo HTML5, tema por `data-theme` + script inline. Backend reusa `httpx`. Cache TTL do Jira em ~15 linhas, sem Redis. O código superado (`src/app/page.tsx` atual) sai da navegação ao entrar o shell e sai do disco na mesma tarefa. |

### Violação registrada

**Restrição técnica violada**: *"Modelos: locais por padrão (Ollama + sentence-transformers). API paga exige ADR justificando custo e saída de dado da máquina."*

O assistente usa OpenRouter (`nvidia/nemotron-3-ultra-550b-a55b:free`). O tier é gratuito, então o argumento de custo não se aplica — mas **o dado sai da máquina**, e modelos gratuitos podem reter prompt para treino do provedor. Isso exige ADR. Ver Complexity Tracking.

### Reavaliação pós-desenho (Fase 1)

Nenhum gate novo foi violado pelo desenho. O que a Fase 1 mudou:

- **Princípio I** — a condição virou mecânica verificável: o corte por `max_distance=0.50` acontece **antes** da chamada ao modelo, e `status: "no_grounding"` é retornado sem que o LLM seja invocado ([api-assistant.md](./contracts/api-assistant.md)). A regra deixou de depender de instrução de prompt.
- **Princípio II** — surgiu um vazamento que o spec não previa: `audit_logs.details_json` seria devolvido inteiro pela timeline. Corrigido com lista branca de chaves por `event_type` ([data-model.md](./data-model.md#timelineevent)).
- **Princípio IV** — o desenho ficou verificável por comando: o cenário 14 do [quickstart.md](./quickstart.md) roda a suíte com as variáveis de credencial removidas do ambiente.
- **Princípio V** — uma redução encontrada no desenho: as quatro seções em construção viraram uma rota dinâmica em vez de quatro páginas idênticas.
- **FR-008** — o protótipo aprovado reprova AA no tema claro (contraste ≈ 2.2:1 no item inativo da sidebar). A divergência está registrada em [research.md R9](./research.md) e no contrato de UI. Requisito venceu protótipo.

A violação da restrição de modelo local permanece a única, e continua exigindo ADR.

## Project Structure

### Documentation (this feature)

```text
specs/002-unified-itsm-agile-ui/
├── plan.md              # Este arquivo
├── spec.md              # Entrada
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/           # Fase 1
│   ├── api-agile.md
│   ├── api-itsm.md
│   ├── api-assistant.md
│   ├── rag-search.md
│   └── ui-routes.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks — não criado aqui)
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/routes.py                    # ALTERA: monta os novos routers
│   ├── api/routes_agile.py              # NOVO
│   ├── api/routes_assistant.py          # NOVO
│   ├── core/config.py                   # ALTERA: jira_board_id, assistant_*, rag_search_url
│   ├── domain/agile.py                  # NOVO: modelos Pydantic de sprint/board/backlog
│   ├── domain/assistant.py              # NOVO: modelos de pergunta/resposta/fonte
│   ├── domain/models.py                 # ALTERA: WorkflowDetailResponse + TimelineEvent
│   ├── integrations/jira_agile.py       # NOVO: leitura de board/sprint/backlog/transições
│   ├── integrations/openrouter.py       # NOVO: cliente chat OpenAI-compatible
│   ├── integrations/rag_search.py       # NOVO: cliente HTTP do serviço de busca
│   ├── repositories/workflows.py        # ALTERA: get_workflow_detail + timeline
│   ├── services/agile.py                # NOVO: burndown, velocity, bloqueios, mapeamento de coluna
│   ├── services/assistant.py            # NOVO: recuperar, redigir, sanitizar
│   └── services/redaction.py            # NOVO: remoção de PII antes do envio ao modelo
└── tests/
    ├── test_agile_routes.py             # NOVO
    ├── test_assistant.py                # NOVO
    ├── test_jira_agile_client.py        # NOVO
    ├── test_redaction.py                # NOVO
    └── test_workflow_detail.py          # NOVO

rag/
├── http/
│   ├── __init__.py                      # NOVO
│   └── app.py                           # NOVO: FastAPI, um endpoint POST /search
├── requirements.txt                     # ALTERA: + fastapi, uvicorn
└── tests/test_http.py                   # NOVO

frontend/src/
├── app/
│   ├── layout.tsx                       # ALTERA: Inter, data-theme, script anti-FOUC
│   ├── globals.css                      # ALTERA: tokens Nocturne + @theme inline
│   ├── page.tsx                         # SUBSTITUI: Home unificada
│   ├── error.tsx  loading.tsx  not-found.tsx   # NOVO
│   ├── itsm/
│   │   ├── page.tsx                     # fila de tickets
│   │   └── [id]/page.tsx                # detalhe + timeline
│   ├── agile/
│   │   ├── page.tsx  backlog/page.tsx  scrum/page.tsx  kanban/page.tsx
│   ├── reports/                         # MOVE de app/analytics/
│   ├── assistant/page.tsx               # NOVO
│   └── em-construcao/[secao]/page.tsx   # NOVO: placeholder nomeado
├── components/
│   ├── shell/                           # sidebar, topbar, workspace-switcher, theme-toggle
│   ├── ui/                              # card, tag, button, table, stat, empty, error, skeleton
│   ├── charts/                          # sparkline, bars, donut, burndown — SVG inline
│   ├── itsm/                            # ticket-table, ticket-filters, timeline, reprocess-button
│   ├── agile/                           # board, column, card (client, DnD nativo), backlog-table
│   └── assistant/                       # chat, message, sources
└── lib/
    ├── api.ts                           # fetch tipado -> Result<T, ApiError>
    ├── nav.ts                           # definição de workspace e seções
    └── types.ts
```

**Structure Decision**: Mantida a separação já existente `backend/` + `frontend/` + `rag/`. Nenhum diretório de topo novo. O frontend passa de duas rotas planas para App Router com um layout raiz que é o shell — o shell vive em `app/layout.tsx` e não num route group, porque **todas** as rotas o usam, e um route group extra sem segunda variante de layout seria abstração sem segunda implementação (Princípio V).

`app/analytics/` vira `app/reports/` por `git mv`, preservando histórico; os componentes internos (`filter-bar`, `upload-screen`, `fields`, `actions`) mudam de estilo, não de lógica.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| **LLM remoto (OpenRouter) em vez de modelo local** — viola *"Modelos: locais por padrão"* | Decisão explícita do autor. Um modelo local de porte suficiente para redigir resposta fundamentada em português não cabe na máquina de demo; Ollama com `qwen3:8b` já está no projeto para classificação de enum, tarefa muito menor. O tier free elimina o argumento de custo. | Ollama local rejeitado por qualidade insuficiente na tarefa de redação. Assistente puramente extrativo (só devolver trechos, sem redação) rejeitado pelo autor. **Exige ADR** em `docs/ai/ai-decisions.md` cobrindo: que dado sai da máquina, que redação de PII é aplicada antes (FR-040), retenção de prompt pelo provedor, e como desligar (`ASSISTANT_ENABLED=false` degrada para modo extrativo). |
| **Serviço HTTP novo em `rag/http/`** — quarto processo no compose | O backend precisa da busca semântica. Importar `rag` direto no backend arrastaria `sentence-transformers` + `torch` (~200 MB CPU-only) para o container da API, que hoje é leve e não tem nenhuma dependência de ML. | Import direto rejeitado pelo peso e por acoplar o container operacional ao de ML. Cliente MCP a partir do backend rejeitado: adiciona `fastmcp` ao backend e gestão de subprocesso stdio para uma única chamada de função. O serviço HTTP é ~40 linhas e reusa `rag.search.query` sem alterá-lo. |
| **Duas dependências novas em `rag/`** (`fastapi`, `uvicorn`) | Consequência direta do item acima. | Nenhuma alternativa: o pacote `rag` não tem servidor HTTP hoje. Ambas já são dependências do backend, então não entram versões novas no repositório. |
| **Cache TTL em processo no backend** | Jira Cloud limita requisição por tenant. Um carregamento de quadro faz 3-4 chamadas a Jira; sem cache, cada navegação do avaliador multiplica isso. | Redis rejeitado (infraestrutura que o MVP não usa, Princípio V). `functools.lru_cache` rejeitado por não expirar — dado de sprint precisa envelhecer. Implementação: dicionário com timestamp, ~15 linhas, TTL de 60 s, invalidado na escrita de transição. |
