# Implementation Plan: Loop fechado Freshservice → Jira com medição do ganho

**Branch**: `001-freshservice-jira-loop` | **Date**: 2026-07-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-freshservice-jira-loop/spec.md`

## Summary

O backend já tem o miolo do tombamento pronto e testado: ingestão idempotente,
outbox, worker com backoff, adaptador Jira, fallback por LLM desligado e
dashboard de exceções. Esta feature fecha o loop em quatro movimentos:

1. **Troca a taxonomia de squad** — `CATEGORY_TO_SQUAD` (enum sintético) sai; a
   squad passa a vir do próprio campo `Squad` do chamado Freshservice, que já
   existe na fonte. O destino no Jira vira um projeto só, com a squad expressa
   como rótulo da issue — em vez de três variáveis de ambiente por projeto.
2. **Substitui webhook por polling** do Freshservice sandbox. O ambiente é
   local; expor a API de ingestão na internet para receber webhook exigiria
   túnel e autenticação de boundary que o MVP não tem. Polling com marca de
   última sincronização elimina os dois problemas e reaproveita o padrão que o
   `data-receiver` já usa.
3. **Porta a trilha analítica do `data-receiver`** (Python): ingestão do export
   do Power BI com detecção por assinatura de coluna, upsert em lote,
   reconstituição do vínculo best-effort por regex de 6 dígitos, e os
   indicadores de squad. Essa base é o "antes".
4. **Marca a origem do vínculo** (`best_effort` × `deterministic`) e expõe a
   comparação. É o número que prova o ganho.

Abordagem: reuso agressivo dos dois repositórios, mínimo de código novo,
nenhuma tabela do fluxo operacional alterada além de duas colunas.

## Technical Context

**Language/Version**: Python 3.12+ (backend), TypeScript/Next.js (frontend, hoje scaffold)

**Primary Dependencies**: FastAPI, SQLAlchemy 2.x, Alembic, psycopg3, httpx, pydantic-settings — todas já presentes. **Novas**: `pandas`, `openpyxl`, `python-multipart` (ver Complexity Tracking)

**Storage**: PostgreSQL — banco operacional existente (`tickets`, `workflow_executions`, `routing_decisions`, `outbox_events`, `jira_issue_links`, `external_references`, `audit_logs`) mais um schema novo `analytics` para a base histórica

**Testing**: pytest + respx (já no grupo dev). Suíte roda sem rede e sem credencial

**Target Platform**: Linux local; Cloud Run permanece destino futuro, não desta feature

**Project Type**: Web service (backend FastAPI) + frontend Next.js

**Performance Goals**: ~3.000 chamados e ~430 cards na carga histórica; tombamento de um chamado em menos de 1 minuto ponta a ponta (SC-002)

**Constraints**: offline-capable para testes; nenhum segredo no repositório; export do Power BI anonimizado antes de qualquer persistência

**Scale/Scope**: 13 squads, 1 projeto Jira sandbox, 1 tenant Freshservice sandbox, usuário único

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Princípio | Como o plano atende | Status |
|---|---|---|
| I — Determinismo primeiro, LLM como fallback medido | Squad vem do campo `Squad` do chamado (determinístico, confiança 1.0). LLM só quando o campo está vazio ou traz valor fora do enum. Golden set existente (`routing_golden.jsonl`) é reescrito para as squads reais antes de qualquer ativação; `LLM_ENABLED=false` continua o padrão | PASS |
| II — Entrada externa não confiável | Enum de squad fechado e validado; texto do chamado nunca vira chave de projeto. Anonimização na entrada da base histórica. Conteúdo de chamado fora de log e de resposta de API mantém o comportamento atual do dashboard (`WorkflowTicketSummary` já omite `requester`) | PASS |
| III — Idempotência e rastreabilidade | Nada muda no núcleo: `uq_ticket_event` continua a chave; polling adiciona uma marca de sincronização, não uma segunda fonte de verdade. Carga histórica usa upsert por identificador de origem | PASS |
| IV — Segredo fora do repositório | Credenciais de sandbox só em `.env`; `.env.example` com placeholder. Suíte verde sem rede via respx e dublês | PASS |
| V — Simples agora | Um projeto Jira em vez de treze; polling em vez de túnel + webhook + autenticação de boundary; módulos portados do `data-receiver` sem reescrita. Três dependências novas justificadas abaixo | PASS com ressalva |

Nenhum gate reprovado. A ressalva do princípio V está registrada em Complexity
Tracking.

**Re-check pós-Fase 1**: os artefatos de design não introduziram violação nova.
`data-model.md` mantém as tabelas operacionais intactas (duas colunas
aditivas, ambas com default) e isola a base histórica em schema próprio.
`contracts/api.md` não adiciona endpoint que dispare efeito externo sem
idempotência. Status inalterado.

## Project Structure

### Documentation (this feature)

```text
specs/001-freshservice-jira-loop/
├── plan.md              # Este arquivo
├── research.md          # Fase 0 — decisões e alternativas
├── data-model.md        # Fase 1 — entidades e migrations
├── quickstart.md        # Fase 1 — roteiro de validação executável
├── contracts/
│   ├── api.md           # Endpoints expostos
│   └── external.md      # Contratos consumidos (Freshservice, Jira)
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 — criado por /speckit-tasks
```

### Source Code (repository root)

```text
backend/
├── app/
│   ├── api/routes.py                   # + rotas de upload, indicadores e comparação
│   ├── core/config.py                  # + credenciais Freshservice, projeto Jira único
│   ├── domain/models.py                # + enum Squad, schemas de upload e indicadores
│   ├── integrations/
│   │   ├── jira.py                     # rótulo de squad + identificador do chamado
│   │   ├── llm.py                      # enum de squad reescrito
│   │   └── freshservice.py             # NOVO — poller com updated_since
│   ├── services/
│   │   ├── routing.py                  # squad do chamado em vez de CATEGORY_TO_SQUAD
│   │   ├── processing.py               # destino Jira por rótulo, não por projeto
│   │   ├── ingestion.py                # inalterado
│   │   └── analytics/                  # NOVO — portado de data-receiver/backend-python
│   │       ├── excel_ingestion.py      # ingest + upsert em lote + regex de vínculo
│   │       ├── upload_detection.py     # assinatura de coluna, teto de tamanho
│   │       ├── anonymization.py        # NOVO — pseudônimo determinístico
│   │       ├── enrichment.py           # join card ↔ chamado
│   │       └── indicators.py           # throughput, distribuição, lead time, cobertura
│   ├── prompts/squad_classifier_v2.txt # enum de squad atualizado
│   └── worker.py                       # + laço de polling do Freshservice
├── migrations/versions/
│   ├── 002_link_origin.py              # NOVO — origem do vínculo + squad no ticket
│   └── 003_analytics_schema.py         # NOVO — schema analytics, 3 tabelas espelho
└── tests/
    ├── golden/routing_golden.jsonl     # reescrito para as squads reais
    └── test_analytics_*.py             # NOVO

frontend/                                # abas de comparação e carga (F5, última)
```

**Structure Decision**: mantém a estrutura existente do `backend/`. A trilha
analítica entra como subpacote `app/services/analytics/` em vez de aplicação
separada — compartilha sessão, configuração e migrations com o fluxo
operacional, e a comparação antes/depois exige as duas bases no mesmo banco.
O `frontend/` só é tocado na última fatia; as fatias anteriores provam tudo por
API e testes.

## Fatias de entrega

Cada fatia é independente e demonstrável. Ordem por prioridade da spec.

| Fatia | Escopo | Cobre | Depende de |
|---|---|---|---|
| **F1 — Taxonomia real** | Squads reais como enum, squad do chamado como regra determinística, projeto Jira único com rótulo, migration `002`, golden set reescrito | FR-003, FR-004, FR-005, FR-009 | — |
| **F2 — Sandbox vivo** | Poller Freshservice, credenciais, marca de sincronização, distinção credencial × conectividade × negócio | FR-001, FR-002, FR-025, FR-026, FR-027 | F1 |
| **F3 — Base histórica** | Schema `analytics`, ingestão do export, anonimização, vínculo best-effort, upload em 2 passos | FR-010 a FR-016 | — (paralelo a F1/F2) |
| **F4 — Comparação** | Indicadores portados, endpoint de cobertura por origem, evidência | FR-017 a FR-020 | F1 + F3 |
| **F5 — Frontend** | Tela de carga, aba de comparação, filtros em cascata | FR-021, e a camada visual de FR-017 a FR-020 | F4 |

FR-006, FR-007, FR-008, FR-022, FR-023 e FR-024 já estão implementados e
cobertos por teste no backend atual — entram como regressão a preservar, não
como trabalho novo. Confirmar antes de escrever código, não depois.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Três dependências novas (`pandas`, `openpyxl`, `python-multipart`) contra o princípio "zero dependência nova" | FR-010 a FR-015 exigem ler `.xlsx` e `.csv` de layout variável, com detecção por assinatura de coluna e contagem de linhas válidas. `openpyxl` é a única forma prática de ler `.xlsx` em Python; `python-multipart` é exigência do FastAPI para receber arquivo; `pandas` é o que o código já validado do `data-receiver` usa | `csv` da stdlib não lê `.xlsx`. Reescrever a ingestão sem pandas significaria reescrever — e revalidar — código que já roda contra os arquivos reais, incluindo tratamento de rodapé, datas em formato variável e o upsert em lote de 1.000 linhas que existe por causa do limite de 65.535 parâmetros bind do Postgres. Custo alto, ganho nenhum |
| Schema `analytics` separado, com tabelas espelho do Excel, em vez de reaproveitar `tickets` | A base histórica descreve chamados que nunca passaram pelo fluxo operacional e não têm execução de workflow. Forçá-los na tabela `tickets` poluiria a métrica do fluxo real e quebraria `uq_ticket_event` | Um flag `is_historical` em `tickets` foi descartado: obrigaria colunas nulas para tudo que só existe no export (27/28 colunas do Freshservice, 15 do Jira) e misturaria as duas populações exatamente na tabela usada para medir o "depois" |
