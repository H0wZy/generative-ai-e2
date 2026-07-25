# Freshservice → Jira MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a locally runnable, PostgreSQL-backed FastAPI service that ingests a Freshservice-compatible payload and creates a real Jira issue through a retryable worker.

**Architecture:** FastAPI validates and persists a normalized event in one PostgreSQL transaction. A worker claims an outbox event, applies deterministic routing, invokes the Jira adapter, and stores an auditable outcome. Every accepted workflow receives an internally generated correlation ID; a supplied external ID is retained only as a reference.

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2, psycopg 3, Alembic, PostgreSQL 16, HTTPX, pytest, Docker Compose.

## Global Constraints

- PostgreSQL is the only operational database; do not use SQLite in `backend/`.
- Freshservice remains synthetic in this increment; no Freshservice secrets are required.
- Jira integration is real but only enabled when runtime credentials are configured.
- Never commit credentials, customer tickets, API tokens or unmasked PII.
- Generate `internal_correlation_id` in the API; retain optional `external_correlation_id` as a non-unique reference.
- n8n is not implemented in this increment and must not own domain rules or idempotency.
- Use TDD for all behavior-changing tasks and preserve all tests in `backend/tests/`.

---

## Planned File Structure

```text
backend/
  app/
    api/routes.py
    core/config.py
    domain/models.py
    integrations/jira.py
    repositories/workflows.py
    services/ingestion.py
    services/processing.py
    worker.py
    main.py
  migrations/versions/001_initial_workflow.py
  tests/
    conftest.py
    test_ingestion.py
    test_processing.py
    test_jira_client.py
  Dockerfile
  pyproject.toml
  .env.example
docker-compose.yml
Makefile
evidence/evaluations/freshservice-jira-mvp.md
docs/architecture/operational-contract.md
```

### Task 1: Replace the exploratory SQLite scaffold with a PostgreSQL service foundation

**Files:**

- Modify: `backend/pyproject.toml`
- Delete: `backend/app/database.py`, `backend/app/service.py`, `backend/app/routing.py`, `backend/app/jira.py`, `backend/app/models.py`, `backend/tests/test_workflow.py`
- Create: `backend/app/core/config.py`, `backend/app/domain/models.py`, `backend/app/main.py`, `backend/tests/conftest.py`, `backend/Dockerfile`, `backend/.env.example`, `docker-compose.yml`
- Modify: `Makefile`

**Interfaces:**

- Produces `Settings` with database and Jira configuration.
- Produces `create_app(settings: Settings) -> FastAPI`.
- Produces a PostgreSQL service at `postgres:5432` for local execution.

- [ ] **Step 1: Write the failing application factory test.**

```python
def test_health_endpoint_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the test to confirm the exploratory scaffold does not satisfy the new factory contract.**

Run: `cd backend && pytest tests/test_health.py -v`

Expected: FAIL because the fixture and PostgreSQL-backed app factory do not exist.

- [ ] **Step 3: Declare runtime and test dependencies.**

```toml
[project]
requires-python = ">=3.12"
dependencies = [
  "alembic>=1.13,<2.0",
  "fastapi>=0.115,<1.0",
  "httpx>=0.27,<1.0",
  "psycopg[binary]>=3.2,<4.0",
  "pydantic-settings>=2.6,<3.0",
  "sqlalchemy>=2.0,<3.0",
  "uvicorn[standard]>=0.30,<1.0",
]

[dependency-groups]
dev = ["pytest>=8.0,<9.0", "respx>=0.21,<1.0"]
```

Create `docker-compose.yml` with a PostgreSQL 16 service, named volume `postgres_data`, database `genai_e2`, user `genai_e2`, and password sourced from `.env`. Create `.env.example` with placeholders only.

- [ ] **Step 4: Implement the factory and configuration.**

```python
class Settings(BaseSettings):
    database_url: PostgresDsn
    jira_base_url: AnyHttpUrl | None = None
    jira_email: str | None = None
    jira_api_token: SecretStr | None = None
    jira_project_identity: str | None = None
    jira_project_finance: str | None = None
    jira_project_platform: str | None = None

def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="GenAI E2 Freshservice to Jira", version="0.1.0")
    app.state.settings = settings or Settings()
    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}
    return app
```

- [ ] **Step 5: Run the focused test and local service checks.**

Run: `cd backend && pytest tests/test_health.py -v`

Expected: PASS.

Run: `docker compose up -d postgres && docker compose exec postgres pg_isready -U genai_e2 -d genai_e2`

Expected: `accepting connections`.

- [ ] **Step 6: Commit the foundation.**

```bash
git add backend docker-compose.yml Makefile
git commit -m "feat: add PostgreSQL backend foundation"
```

### Task 2: Persist an idempotent ticket ingestion with internal and external correlation IDs

**Files:**

- Create: `backend/app/repositories/workflows.py`, `backend/app/services/ingestion.py`, `backend/app/api/routes.py`, `backend/migrations/versions/001_initial_workflow.py`
- Modify: `backend/app/domain/models.py`, `backend/app/main.py`, `backend/tests/conftest.py`
- Create: `backend/tests/test_ingestion.py`

**Interfaces:**

- Consumes `TicketIngestRequest` from `domain/models.py`.
- Produces `IngestResult(workflow_execution_id: UUID, internal_correlation_id: UUID, status: Literal["accepted", "duplicate"])`.
- `WorkflowRepository.ingest(...)` writes ticket, workflow, external reference, outbox event and audit event in one transaction.

- [ ] **Step 1: Write failing idempotency and correlation tests.**

```python
def test_ingest_generates_internal_id_and_preserves_external_reference(client):
    response = client.post("/api/v1/tickets/ingest", json=synthetic_ticket())
    assert response.status_code == 202
    body = response.json()
    assert UUID(body["internal_correlation_id"])
    assert body["internal_correlation_id"] != "n8n-execution-001"

def test_same_source_event_returns_existing_execution(client):
    first = client.post("/api/v1/tickets/ingest", json=synthetic_ticket())
    second = client.post("/api/v1/tickets/ingest", json=synthetic_ticket())
    assert second.json()["status"] == "duplicate"
    assert second.json()["workflow_execution_id"] == first.json()["workflow_execution_id"]
```

- [ ] **Step 2: Run the focused tests.**

Run: `cd backend && pytest tests/test_ingestion.py -v`

Expected: FAIL because no route, migration or repository exists.

- [ ] **Step 3: Define validated request and response types.**

```python
class TicketIngestRequest(BaseModel):
    event_id: Annotated[str, Field(min_length=1, max_length=128)]
    event_type: Literal["ticket.created", "ticket.updated"]
    occurred_at: datetime
    source_ticket_id: Annotated[str, Field(min_length=1, max_length=80)]
    subject: Annotated[str, Field(min_length=1, max_length=255)]
    description: Annotated[str, Field(max_length=20_000)] = ""
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    category: str | None = None
    requester: str | None = None
    attachments: list[Attachment] = Field(default_factory=list)
    external_correlation_id: str | None = Field(default=None, max_length=128)

class IngestResponse(BaseModel):
    workflow_execution_id: UUID
    internal_correlation_id: UUID
    status: Literal["accepted", "duplicate"]

@dataclass(frozen=True)
class TicketRecord:
    id: UUID
    source_ticket_id: str
    subject: str
    description: str
    priority: str
    category: str | None
```

- [ ] **Step 4: Add the migration and atomic ingestion repository.**

The migration creates `tickets`, `workflow_executions`, `external_references`, `routing_decisions`, `outbox_events`, `jira_issue_links` and `audit_logs`. It creates a unique index on `(source_system, source_ticket_id, event_type, event_id)` and a non-unique index on `(source_system, external_correlation_id)`. The repository must insert an `outbox_events` row and `ticket.ingested` audit row in the same transaction; on unique conflict it returns the existing workflow without creating new records.

- [ ] **Step 5: Expose the route.**

```python
@router.post("/api/v1/tickets/ingest", status_code=status.HTTP_202_ACCEPTED)
def ingest_ticket(payload: TicketIngestRequest, service: IngestionService = Depends(get_ingestion_service)) -> IngestResponse:
    return service.ingest(payload)
```

- [ ] **Step 6: Run migration and tests.**

Run: `cd backend && alembic upgrade head && pytest tests/test_ingestion.py -v`

Expected: migration succeeds and both tests PASS.

- [ ] **Step 7: Commit ingestion.**

```bash
git add backend
git commit -m "feat: add idempotent ticket ingestion"
```

### Task 3: Implement deterministic routing and worker state transitions

**Files:**

- Create: `backend/app/services/routing.py`, `backend/app/services/processing.py`, `backend/app/worker.py`, `backend/tests/test_processing.py`
- Modify: `backend/app/repositories/workflows.py`, `backend/app/domain/models.py`

**Interfaces:**

- `route_ticket(category: str | None) -> RoutingDecision` returns a squad or manual review.
- `ProcessingService.process_next() -> ProcessResult | None` claims one pending outbox event.
- Produces workflow states `pending`, `processing`, `completed`, `retry_scheduled`, `failed` and `needs_human_review`.

- [ ] **Step 1: Write failing routing tests.**

```python
@pytest.mark.parametrize(("category", "squad"), [
    ("access", "identity"),
    ("billing", "finance"),
    ("incident", "platform"),
    ("integration", "platform"),
])
def test_known_categories_route_deterministically(category, squad):
    assert route_ticket(category).squad_id == squad

def test_unknown_category_requires_human_review():
    decision = route_ticket("unknown")
    assert decision.needs_human_review is True
    assert decision.squad_id is None
```

- [ ] **Step 2: Run the focused tests.**

Run: `cd backend && pytest tests/test_processing.py -v`

Expected: FAIL because routing and worker services do not exist.

- [ ] **Step 3: Implement routing and transactional worker claim.**

```python
CATEGORY_TO_SQUAD = {"access": "identity", "billing": "finance", "incident": "platform", "integration": "platform"}

def route_ticket(category: str | None) -> RoutingDecision:
    normalized = (category or "").strip().lower()
    squad_id = CATEGORY_TO_SQUAD.get(normalized)
    if squad_id:
        return RoutingDecision(squad_id, "routing-rules/v1", 1.0, False)
    return RoutingDecision(None, "routing-rules/v1:no-match", 0.0, True)

@dataclass(frozen=True)
class ProcessResult:
    workflow_execution_id: UUID
    status: Literal["completed", "retry_scheduled", "failed", "needs_human_review"]
    attempt_count: int
    jira_issue_key: str | None
```

`claim_next` uses `SELECT ... FOR UPDATE SKIP LOCKED`, sets status to `processing`, increments attempts and returns the claimed execution. An unmatched decision stores a routing decision, sets `needs_human_review`, completes the outbox event and writes `routing.review_required` to audit.

- [ ] **Step 4: Run the focused tests.**

Run: `cd backend && pytest tests/test_processing.py -v`

Expected: PASS.

- [ ] **Step 5: Commit routing and worker state.**

```bash
git add backend
git commit -m "feat: add deterministic workflow routing"
```

### Task 4: Add the real Jira adapter, retry policy and idempotent issue linking

**Files:**

- Create: `backend/app/integrations/jira.py`, `backend/tests/test_jira_client.py`
- Modify: `backend/app/core/config.py`, `backend/app/services/processing.py`, `backend/app/repositories/workflows.py`, `backend/tests/test_processing.py`

**Interfaces:**

- `JiraClient.create_issue(ticket: TicketRecord, project_key: str, internal_correlation_id: UUID) -> str`.
- `JiraClientError(retryable: bool, message: str)` classifies provider errors.
- Jira project lookup uses the squad-specific configuration in `Settings`.

- [ ] **Step 1: Write failing adapter and retry tests.**

```python
def test_jira_client_sends_external_reference_and_internal_trace(respx_mock, jira_client, ticket):
    respx_mock.post("https://example.atlassian.net/rest/api/3/issue").respond(201, json={"key": "PLAT-123"})
    assert jira_client.create_issue(ticket, "PLAT", UUID("018f0d8a-3d8e-7eef-93b6-2f0b11d31ee0")) == "PLAT-123"

def test_retryable_jira_error_schedules_retry(processing_service, pending_workflow, fake_jira):
    fake_jira.raise_error(JiraClientError(retryable=True, message="gateway timeout"))
    result = processing_service.process_next()
    assert result.status == "retry_scheduled"
    assert result.attempt_count == 1
```

- [ ] **Step 2: Run the focused tests.**

Run: `cd backend && pytest tests/test_jira_client.py tests/test_processing.py -v`

Expected: FAIL because no Jira adapter or retry policy exists.

- [ ] **Step 3: Implement the HTTP adapter.**

```python
payload = {
    "fields": {
        "project": {"key": project_key},
        "summary": ticket.subject,
        "description": to_atlassian_document(ticket.description),
        "labels": [f"freshservice-{ticket.source_ticket_id}", f"trace-{internal_correlation_id}"],
    },
}
response = self._client.post("/rest/api/3/issue", json=payload)

def to_atlassian_document(text: str) -> dict:
    return {
        "type": "doc",
        "version": 1,
        "content": [{"type": "paragraph", "content": [{"type": "text", "text": text or "-"}]}],
    }
```

Use basic authentication from runtime settings, map HTTP `408`, `429` and `5xx` to retryable errors, and map other `4xx` responses to terminal errors. Check the existing `jira_issue_links` record before any call and create the link in the same transaction that records completion.

- [ ] **Step 4: Implement retry scheduling.**

Use `next_attempt_at = now + min(300, 2 ** attempt_count) + random.uniform(0, 1)`. Set `retry_scheduled` for retryable failures below the configured maximum of 5 attempts; otherwise set `failed`. In each branch, write a sanitized audit event without request headers, tokens or ticket body.

- [ ] **Step 5: Run the focused tests.**

Run: `cd backend && pytest tests/test_jira_client.py tests/test_processing.py -v`

Expected: PASS.

- [ ] **Step 6: Commit the Jira integration.**

```bash
git add backend
git commit -m "feat: integrate Jira worker with retries"
```

### Task 5: Make the MVP runnable and document the evidence trail

**Files:**

- Modify: `README.md`, `docs/architecture/operational-contract.md`, `docs/superpowers/specs/2026-07-25-freshservice-jira-mvp-design.md`
- Create: `backend/tests/fixtures/ticket_created.json`, `evidence/evaluations/freshservice-jira-mvp.md`
- Modify: `Makefile`

**Interfaces:**

- Produces `make up`, `make migrate`, `make test`, `make ingest-demo` and `make worker-once`.
- Produces a reproducible synthetic demonstration and evidence record.

- [ ] **Step 1: Write a failing end-to-end test with the JSON fixture.**

```python
def test_fixture_ingests_then_worker_creates_expected_jira_link(client, fake_jira, fixture_payload):
    accepted = client.post("/api/v1/tickets/ingest", json=fixture_payload)
    processed = client.post("/api/v1/workflows/process-next")
    assert accepted.status_code == 202
    assert processed.status_code == 200
    assert processed.json()["status"] == "completed"
    assert processed.json()["jira_issue_key"] == "PLAT-123"
```

- [ ] **Step 2: Run the full test suite.**

Run: `cd backend && pytest -v`

Expected: FAIL until fixture wiring and worker test endpoint/command are complete.

- [ ] **Step 3: Add reproducible commands and documentation.**

```make
up:
	docker compose up -d postgres
migrate:
	cd backend && alembic upgrade head
test:
	cd backend && pytest -v
worker-once:
	cd backend && python -m app.worker --once
```

Document real Jira prerequisites, synthetic-only Freshservice input, environment variable names, no-secret policy, expected demo output, and the distinction between `internal_correlation_id` and `external_correlation_id`.

- [ ] **Step 4: Run the full verification sequence.**

Run: `cp backend/.env.example backend/.env && docker compose up -d postgres && make migrate && make test`

Expected: PostgreSQL is healthy, migrations apply and all tests PASS.

- [ ] **Step 5: Record sanitized evidence.**

Write the fixture name, test command, pass result, routing outcome, correlation-ID behavior, known limitations and reviewer/date in `evidence/evaluations/freshservice-jira-mvp.md`.

- [ ] **Step 6: Commit MVP documentation and evidence.**

```bash
git add README.md docs evidence backend/tests/fixtures Makefile
git commit -m "docs: add Freshservice Jira MVP runbook"
```

## GitHub Backlog Mapping

| GitHub item | Plan task | Acceptance signal |
|---|---|---|
| Epic: MVP Freshservice → Jira | All | All child issues are closed and demo evidence exists |
| Issue: PostgreSQL backend foundation | Task 1 | Health test and PostgreSQL health check pass |
| Issue: Idempotent ingestion and audit trail | Task 2 | Duplicate and correlation tests pass |
| Issue: Deterministic routing worker | Task 3 | Known routes and manual-review route pass |
| Issue: Real Jira adapter and retry policy | Task 4 | Mocked HTTP and retry tests pass; real smoke test is opt-in |
| Issue: MVP runbook and evidence | Task 5 | Full test suite and sanitized evidence recorded |

## Plan Self-Review

- **Spec coverage:** all MVP components, external-ID handling, Jira real integration, persistence, retry, testing, documentation and GitHub traceability map to a task.
- **Placeholder scan:** no unassigned tasks or unspecified acceptance criteria remain; Freshservice and n8n are explicitly excluded.
- **Type consistency:** API payload uses `external_correlation_id`; API-generated `internal_correlation_id` is propagated through the repository, worker and Jira adapter.
