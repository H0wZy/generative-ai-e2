# Freshservice → Jira MVP Design

**Status:** approved for planning on 2026-07-25.

## Goal

Deliver a locally runnable MVP that accepts a normalized Freshservice-compatible ticket payload, routes it deterministically, creates a real Jira issue, and preserves a complete operational trail in PostgreSQL.

## Scope

### Included

- FastAPI endpoint for versioned ticket ingestion.
- Synthetic fixtures that emulate the normalized Freshservice webhook payload.
- PostgreSQL persistence for tickets, workflow executions, idempotency, routing decisions, Jira links and audit events.
- Worker process that claims pending work and calls the Jira REST API.
- Deterministic squad routing for the initial supported categories.
- Retry state for transient Jira failures and explicit terminal failure state for future DLQ handling.
- Real Jira integration configured only through environment variables or a secret manager.
- Automated tests, local run instructions, architecture records and implementation evidence.
- GitHub epic, implementation issues and kanban board that trace back to the plan.

### Excluded

- Freshservice credentials and a live Freshservice webhook.
- n8n deployment; its future role is limited to validating/adapting the vendor webhook and calling the FastAPI endpoint.
- LLM-based routing, human-review interface, attachment transfer, dashboard, RAG/MCP and OCR.
- A shared or Cloud Run-hosted SQLite database.

## Architecture

```text
Synthetic Freshservice-compatible payload
                 │
                 ▼
       FastAPI POST /api/v1/tickets/ingest
                 │
                 ▼
 PostgreSQL: ticket + execution + idempotency + audit
                 │
                 ▼
          worker claims pending execution
                 │
                 ▼
       deterministic routing → Jira REST API
                 │
                 ▼
  Jira link + completion/failure audit persisted in PostgreSQL
```

FastAPI owns schema validation and transactional persistence. PostgreSQL is the source of truth. The worker owns external side effects and retry state. The Jira client is an isolated adapter so tests can replace it with a deterministic fake. n8n and Freshservice remain outside the domain boundary.

## Component Boundaries

| Component | Responsibility | Boundary |
|---|---|---|
| `api` | Validate HTTP requests and map domain results to responses | Does not call Jira |
| `domain` | Ticket, routing and workflow types | Does not access database/network |
| `repositories` | PostgreSQL commands and transactions | Does not apply business rules |
| `services` | Ingestion, idempotency, routing state transitions | Depends on repository interfaces |
| `integrations/jira` | Jira REST API authentication and issue creation | Does not decide routing/state |
| `worker` | Claim pending execution, invoke service and schedule retry | Does not expose public API |

## API Contract

`POST /api/v1/tickets/ingest` accepts a normalized payload with:

```json
{
  "event_id": "evt-001",
  "event_type": "ticket.created",
  "occurred_at": "2026-07-25T12:00:00Z",
  "source_ticket_id": "FS-100",
  "subject": "Servico indisponivel",
  "description": "Aplicacao nao responde.",
  "priority": "high",
  "category": "incident",
  "requester": "user@example.test",
  "attachments": [],
  "external_correlation_id": "n8n-execution-001"
}
```

The endpoint generates an `internal_correlation_id` for every accepted workflow and returns it with `workflow_execution_id` and `accepted` or `duplicate`. The optional `external_correlation_id` is stored for reconciliation with Freshservice or n8n, but is never used as an idempotency key, authorization input or primary identifier. The idempotency key is unique for `source_system`, `source_ticket_id`, `event_type` and source event version. The final source-event version field is added before Freshservice is connected.

## Data Model

- `tickets`: normalized source ticket and safe metadata.
- `workflow_executions`: lifecycle, internally generated correlation ID, retry count, schedule and last error.
- `external_references`: optional source-system correlation IDs retained for reconciliation and investigation.
- `routing_decisions`: rule version, squad, confidence and reason.
- `jira_issue_links`: one unique Jira issue key per ticket.
- `outbox_events`: transactional work records consumed by the worker.
- `audit_logs`: append-only status transitions with sanitized details.

The MVP uses PostgreSQL in local Docker Compose and tests use an isolated PostgreSQL database. SQLite is not used by this automation domain.

## Routing and State Transitions

The first rules map `access` to `identity`, `billing` to `finance`, and `incident` or `integration` to `platform`. Unmatched categories transition to `needs_human_review`; no Jira issue is created for them.

Workflow states are `pending`, `processing`, `completed`, `retry_scheduled`, `failed` and `needs_human_review`. The worker claims a pending item in a transaction. Recoverable Jira failures increment attempts and schedule exponential backoff with jitter. A nonrecoverable response or exhausted attempts transitions to `failed` and records an audit event.

## Jira Integration

The adapter requires `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` and a configured project key for each squad. No default credentials, tokens or URLs are committed. It sends a minimal issue payload containing summary, description, priority and an external-reference label/property based on the Freshservice ticket ID. A test fake verifies behavior without external network calls.

## Security and Observability

- Reject malformed payloads and authenticate the future n8n caller.
- Keep credentials only in runtime environment variables for local development and Secret Manager for deployment.
- Generate the internal correlation ID at the FastAPI boundary and preserve it across worker execution, retries, audit records and Jira calls.
- Log internal correlation ID, optional external correlation ID, workflow ID, source ticket ID, operation, status, duration and sanitized error category.
- Do not log ticket descriptions, requester PII, attachments or authentication headers by default.
- Expose a health endpoint and metrics-ready counters for received, completed, retried, failed and duplicate requests.

## Testing and Demonstration

Tests cover validation, idempotent duplicate ingestion, deterministic routing, manual-review routing, Jira success, transient retry and terminal Jira failure. A local demonstration uses a synthetic payload and a fake Jira adapter; the real adapter is smoke-tested only when safe credentials are supplied.

## Documentation and GitHub Traceability

The implementation plan is stored in `docs/superpowers/plans/`. The GitHub epic and child issues each link to the plan section and include acceptance criteria. The kanban uses `Backlog`, `In Progress`, `Review`, `Done` and `Blocked`. Implementation evidence goes to `evidence/architecture`, `evidence/decisions`, `evidence/demos` and `evidence/evaluations` without sensitive data.
