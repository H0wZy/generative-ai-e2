"""Tests for deterministic routing and ProcessingService state transitions."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.integrations.jira import FakeJiraClient, JiraClientError
from app.services.routing import route_ticket
from tests.conftest import synthetic_ticket


# ---------------------------------------------------------------------------
# Pure routing unit tests — no DB, no HTTP
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("squad", "expected_squad"),
    [
        ("SQUAD-04", "SQUAD-04"),
        ("SQUAD-03", "SQUAD-03"),
        ("SQUAD-08", "SQUAD-08"),
        ("squad04", "SQUAD-04"),        # case insensitive
        ("  squad 04  ", "SQUAD-04"),   # whitespace and separator tolerant
        ("squad-08", "SQUAD-08"),
    ],
)
def test_known_squads_route_deterministically(squad: str, expected_squad: str) -> None:
    decision = route_ticket(squad)
    assert decision.squad_id == expected_squad
    assert decision.needs_human_review is False
    assert decision.confidence == 1.0
    assert decision.rule_version == "routing-rules/v2"


@pytest.mark.parametrize("squad", [None, "", "unknown", "Squad3", "admin", "xyz"])
def test_unknown_squad_requires_human_review(squad) -> None:
    """Missing squad and squad outside the closed enum are the same case.

    Squad3 is the interesting one: the old best-effort link rule invented it
    from an issue-key prefix, and it does not exist in Freshservice.
    """
    decision = route_ticket(squad)
    assert decision.needs_human_review is True
    assert decision.squad_id is None
    assert decision.confidence == 0.0


# ---------------------------------------------------------------------------
# Integration tests — ingest then process via HTTP
# ---------------------------------------------------------------------------


def test_process_next_creates_jira_link_for_known_squad(client: TestClient) -> None:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))

    processed = client.post("/api/v1/workflows/process-next")
    assert processed.status_code == 200
    body = processed.json()
    assert body["status"] == "completed"
    assert body["jira_issue_key"] == "SQD-123"
    assert body["attempt_count"] == 1


def test_every_squad_lands_in_the_single_configured_project(
    client: TestClient, fake_jira: FakeJiraClient
) -> None:
    """Two different squads, same project — told apart by the label."""
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))
    client.post("/api/v1/workflows/process-next")
    assert "squad-SQUAD-04" in fake_jira.last_labels

    client.post(
        "/api/v1/tickets/ingest",
        json=synthetic_ticket(event_id="evt-002", source_ticket_id="FS-101", squad="SQUAD-02"),
    )
    client.post("/api/v1/workflows/process-next")
    assert "squad-SQUAD-02" in fake_jira.last_labels
    assert "freshservice-FS-101" in fake_jira.last_labels


def test_completed_link_records_deterministic_origin(client: TestClient) -> None:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))
    client.post("/api/v1/workflows/process-next")

    item = client.get("/api/v1/workflows").json()["items"][0]
    assert item["link_origin"] == "deterministic"


def test_process_next_marks_needs_human_review_for_unknown_squad(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/tickets/ingest",
        json=synthetic_ticket(
            event_id="evt-review",
            source_ticket_id="FS-200",
            squad=None,
        ),
    )
    processed = client.post("/api/v1/workflows/process-next")
    assert processed.status_code == 200
    assert processed.json()["status"] == "needs_human_review"
    assert processed.json()["jira_issue_key"] is None


def test_process_next_returns_queue_empty_when_nothing_pending(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/workflows/process-next")
    assert response.status_code == 200
    assert response.json()["status"] == "queue_empty"


def test_process_next_retryable_error_schedules_retry(
    db_session,
    session_factory,
    test_settings,
    fake_jira: FakeJiraClient,
) -> None:
    """ProcessingService schedules retry on retryable Jira error."""
    from sqlalchemy.orm import Session
    from app.services.ingestion import IngestionService
    from app.services.processing import ProcessingService
    from app.domain.models import TicketIngestRequest
    from datetime import datetime, timezone

    session = session_factory()
    try:
        ingest_svc = IngestionService(session)
        ingest_svc.ingest(
            TicketIngestRequest(
                event_id="evt-retry",
                event_type="ticket.created",
                occurred_at=datetime.now(timezone.utc),
                source_ticket_id="FS-999",
                subject="Test retry",
                category="incident",
                squad="SQUAD-04",
            )
        )
    finally:
        session.close()

    fake_jira.raise_error(JiraClientError(retryable=True, message="gateway timeout"))

    session2 = session_factory()
    try:
        result = ProcessingService(session2, fake_jira, test_settings).process_next()
    finally:
        session2.close()

    assert result is not None
    assert result.status == "retry_scheduled"
    assert result.attempt_count == 1


def test_process_next_terminal_error_marks_failed(
    session_factory,
    test_settings,
    fake_jira: FakeJiraClient,
) -> None:
    from sqlalchemy.orm import Session
    from app.services.ingestion import IngestionService
    from app.services.processing import ProcessingService
    from app.domain.models import TicketIngestRequest
    from datetime import datetime, timezone

    session = session_factory()
    try:
        IngestionService(session).ingest(
            TicketIngestRequest(
                event_id="evt-terminal",
                event_type="ticket.created",
                occurred_at=datetime.now(timezone.utc),
                source_ticket_id="FS-888",
                subject="Test terminal failure",
                category="incident",
                squad="SQUAD-04",
            )
        )
    finally:
        session.close()

    fake_jira.raise_error(JiraClientError(retryable=False, message="invalid project"))

    session2 = session_factory()
    try:
        result = ProcessingService(session2, fake_jira, test_settings).process_next()
    finally:
        session2.close()

    assert result is not None
    assert result.status == "failed"


@pytest.mark.parametrize("http_status", [401, 503])
def test_last_error_never_leaks_jira_response_body(
    client: TestClient,
    session_factory,
    test_database_url: str,
    http_status: int,
) -> None:
    """last_error must be built from HTTP status only — never response body,
    exc text or the Jira base URL. Locks JiraClient._raise_for_status against
    a future switch to str(exc) / response.text, which would leak Jira
    tenant secrets straight into the dashboard (and demo recordings).
    """
    from datetime import datetime, timezone

    import respx

    from app.core.config import Settings
    from app.domain.models import TicketIngestRequest
    from app.integrations.jira import JiraClient
    from app.services.ingestion import IngestionService
    from app.services.processing import ProcessingService

    jira_url = "https://acme.atlassian.net"
    malicious_body = {
        "errorMessages": ["Unauthorized"],
        "token": "fake-secret-abc123",
        "url": jira_url,
        "email": "alguem@acme.com",
    }

    session = session_factory()
    try:
        IngestionService(session).ingest(
            TicketIngestRequest(
                event_id=f"evt-leak-{http_status}",
                event_type="ticket.created",
                occurred_at=datetime.now(timezone.utc),
                source_ticket_id=f"FS-leak-{http_status}",
                subject="Test last_error sanitization",
                category="incident",
                squad="SQUAD-04",
            )
        )
    finally:
        session.close()

    settings = Settings(
        database_url=test_database_url,  # type: ignore[arg-type]
        jira_base_url=jira_url,  # type: ignore[arg-type]
        jira_email="admin@acme.com",
        jira_api_token="admin-token",  # type: ignore[arg-type]
        jira_project_key="SQD",
    )
    real_jira = JiraClient(settings)

    with respx.mock:
        respx.post(f"{jira_url}/rest/api/3/issue").respond(http_status, json=malicious_body)
        session2 = session_factory()
        try:
            result = ProcessingService(session2, real_jira, settings).process_next()
        finally:
            session2.close()

    assert result is not None
    assert result.status in ("failed", "retry_scheduled")

    listed = client.get("/api/v1/workflows").json()
    last_error = listed["items"][0]["last_error"]

    for marker in ("fake-secret-abc123", "atlassian.net", "alguem@acme.com"):
        assert marker not in last_error

    prefix = "retryable:" if result.status == "retry_scheduled" else "terminal:"
    assert last_error == f"{prefix}HTTP {http_status}"
