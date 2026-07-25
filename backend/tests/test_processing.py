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
    ("category", "expected_squad"),
    [
        ("access", "identity"),
        ("billing", "finance"),
        ("incident", "platform"),
        ("integration", "platform"),
        ("ACCESS", "identity"),   # case insensitive
        ("  billing  ", "finance"),  # whitespace trimmed
    ],
)
def test_known_categories_route_deterministically(category: str, expected_squad: str) -> None:
    decision = route_ticket(category)
    assert decision.squad_id == expected_squad
    assert decision.needs_human_review is False
    assert decision.confidence == 1.0


@pytest.mark.parametrize("category", [None, "", "unknown", "hardware", "xyz"])
def test_unknown_category_requires_human_review(category) -> None:
    decision = route_ticket(category)
    assert decision.needs_human_review is True
    assert decision.squad_id is None
    assert decision.confidence == 0.0


# ---------------------------------------------------------------------------
# Integration tests — ingest then process via HTTP
# ---------------------------------------------------------------------------


def test_process_next_creates_jira_link_for_incident(client: TestClient) -> None:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(category="incident"))

    processed = client.post("/api/v1/workflows/process-next")
    assert processed.status_code == 200
    body = processed.json()
    assert body["status"] == "completed"
    assert body["jira_issue_key"] == "PLAT-123"
    assert body["attempt_count"] == 1


def test_process_next_marks_needs_human_review_for_unknown_category(
    client: TestClient,
) -> None:
    client.post(
        "/api/v1/tickets/ingest",
        json=synthetic_ticket(
            event_id="evt-review",
            source_ticket_id="FS-200",
            category="hardware",
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
