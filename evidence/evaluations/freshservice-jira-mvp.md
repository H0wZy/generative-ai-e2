# Evidência — MVP Freshservice → Jira

**Data:** 2026-07-25  
**Revisor:** implementação automatizada + revisão manual  
**Status:** COMPLETO

---

## Resumo

Implementação completa do MVP PostgreSQL + FastAPI + Worker + Jira conforme o plano versionado em `docs/superpowers/plans/2026-07-25-freshservice-jira-mvp.md`.

## Artefatos

| Arquivo | Descrição |
|---|---|
| `backend/tests/fixtures/ticket_created.json` | Fixture sintética do webhook Freshservice |
| `backend/migrations/versions/001_initial_workflow.py` | Migração Alembic com schema completo |
| `backend/app/core/config.py` | Settings via pydantic-settings |
| `backend/app/domain/models.py` | Tipos de domínio puros |
| `backend/app/repositories/schema.py` | ORM SQLAlchemy (7 tabelas) |
| `backend/app/repositories/workflows.py` | Repositório atômico PostgreSQL |
| `backend/app/services/ingestion.py` | IngestionService com idempotência |
| `backend/app/services/routing.py` | Roteamento determinístico |
| `backend/app/services/processing.py` | ProcessingService + retry/backoff |
| `backend/app/integrations/jira.py` | JiraClient real + FakeJiraClient |
| `backend/app/api/routes.py` | Rotas FastAPI |
| `backend/app/worker.py` | Worker standalone CLI |

## Execução dos Testes

```
Comando: cd backend && TEST_DATABASE_URL=postgresql://genai_e2:***@localhost:5432/genai_e2_test python -m pytest -v
Resultado: 31 passed, 1 warning in 1.19s
```

### Cobertura dos critérios de aceite

| Critério | Status | Evidência |
|---|---|---|
| Health endpoint retorna `{"status": "ok"}` | ✅ PASS | test_health.py::test_health_endpoint_returns_ok |
| Ingestão gera `internal_correlation_id` UUID diferente do externo | ✅ PASS | test_ingestion.py::test_ingest_returns_202_with_uuid_correlation_id |
| Duplicata retorna mesmo `workflow_execution_id` | ✅ PASS | test_ingestion.py::test_same_source_event_returns_duplicate |
| Sem `external_correlation_id` é aceito | ✅ PASS | test_ingestion.py::test_ingest_without_external_correlation_id |
| Validação rejeita subject vazio | ✅ PASS | test_ingestion.py::test_ingest_rejects_empty_subject |
| Roteamento `incident` → `platform` | ✅ PASS | test_processing.py parametrizado |
| Roteamento `access` → `identity` | ✅ PASS | test_processing.py parametrizado |
| Roteamento `billing` → `finance` | ✅ PASS | test_processing.py parametrizado |
| Categoria desconhecida → `needs_human_review` | ✅ PASS | test_processing.py::test_unknown_category_requires_human_review |
| Worker completa com link Jira | ✅ PASS | test_processing.py::test_process_next_creates_jira_link_for_incident |
| Fila vazia retorna `queue_empty` | ✅ PASS | test_processing.py::test_process_next_returns_queue_empty_when_nothing_pending |
| Erro retryable agenda retry | ✅ PASS | test_processing.py::test_process_next_retryable_error_schedules_retry |
| Erro terminal → `failed` | ✅ PASS | test_processing.py::test_process_next_terminal_error_marks_failed |
| JiraClient envia labels `freshservice-*` e `trace-*` | ✅ PASS | test_jira_client.py::test_jira_client_sends_freshservice_label_and_trace |
| JiraClient retryable em 5xx | ✅ PASS | test_jira_client.py::test_jira_client_raises_retryable_on_5xx |
| JiraClient terminal em 4xx | ✅ PASS | test_jira_client.py::test_jira_client_raises_terminal_on_4xx |
| E2E: fixture → worker → PLAT-123 | ✅ PASS | test_e2e.py::test_fixture_ingests_then_worker_creates_expected_jira_link |
| E2E: duplicata reutiliza workflow | ✅ PASS | test_e2e.py::test_duplicate_fixture_reuses_existing_workflow |

## Comportamento de Correlation IDs

- `internal_correlation_id`: UUID v4 gerado no boundary do FastAPI, propagado por todo o repositório, worker, logs de auditoria e labels do Jira.
- `external_correlation_id`: campo opcional, armazenado na tabela `external_references` apenas para reconciliação. Nunca usado como chave de idempotência, autorização ou identificador primário.

## Roteamento

Regras determinísticas implementadas em `services/routing.py`:

| Categoria | Squad | Confiança |
|---|---|---|
| `access` | `identity` | 1.0 |
| `billing` | `finance` | 1.0 |
| `incident` | `platform` | 1.0 |
| `integration` | `platform` | 1.0 |
| qualquer outro | (nenhum) | 0.0 — needs_human_review |

## Limitações Conhecidas

- Freshservice permanece sintético neste incremento — nenhuma credencial real é usada.
- n8n não foi implementado — está fora do escopo do MVP.
- Sem LLM para roteamento de ambiguidades (pós-MVP).
- Sem dashboard, OCR ou transferência de anexos (pós-MVP).
- Jira real requer configuração de `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` e chaves de projeto no `.env`.

## Segurança

- Nenhum segredo, PII ou dado real de ticket incluído.
- Todos os valores em `.env.example` são placeholders.
- Dados de teste são sintéticos (`user@example.test`, `FS-100`).
