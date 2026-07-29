"""Tests for GET /workflows/{id} — timeline, 404 and detail whitelisting."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from app.integrations.jira import FakeJiraClient, JiraClientError
from tests.conftest import synthetic_ticket


def _ingest_and_process(client: TestClient, **kwargs) -> str:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(**kwargs))
    client.post("/api/v1/workflows/process-next")
    return client.get("/api/v1/workflows").json()["items"][0]["workflow_execution_id"]


def test_detail_returns_404_for_unknown_id(client: TestClient) -> None:
    response = client.get(f"/api/v1/workflows/{uuid.uuid4()}")
    assert response.status_code == 404


def test_timeline_is_chronological(client: TestClient) -> None:
    workflow_id = _ingest_and_process(client, squad="SQUAD-04")

    body = client.get(f"/api/v1/workflows/{workflow_id}").json()
    timestamps = [event["at"] for event in body["timeline"]]
    assert timestamps == sorted(timestamps)
    assert body["timeline"][0]["event_type"] == "ticket.ingested"
    assert body["timeline"][0]["summary"] == "Ticket recebido"


def test_detail_never_carries_ticket_subject_or_description(client: TestClient) -> None:
    """A lista branca por event_type é o que impede o vazamento."""
    workflow_id = _ingest_and_process(client, squad="SQUAD-04")

    body = client.get(f"/api/v1/workflows/{workflow_id}").json()
    ticket = body["ticket"]
    for event in body["timeline"]:
        serialized = str(event["detail"])
        assert ticket["subject"] not in serialized
        assert ticket["description"] not in serialized


def test_reprocess_eligible_true_for_failed(client: TestClient, fake_jira: FakeJiraClient) -> None:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))
    fake_jira.raise_error(JiraClientError(retryable=False, message="invalid project"))
    client.post("/api/v1/workflows/process-next")
    workflow_id = client.get("/api/v1/workflows").json()["items"][0]["workflow_execution_id"]

    body = client.get(f"/api/v1/workflows/{workflow_id}").json()
    assert body["status"] == "failed"
    assert body["reprocess_eligible"] is True


def test_reprocess_eligible_false_for_completed(client: TestClient) -> None:
    workflow_id = _ingest_and_process(client, squad="SQUAD-04")

    body = client.get(f"/api/v1/workflows/{workflow_id}").json()
    assert body["status"] == "completed"
    assert body["reprocess_eligible"] is False


def test_jira_issue_url_is_none_without_configured_base_url(client: TestClient) -> None:
    """test_settings não configura JIRA_BASE_URL — sem base, sem link."""
    workflow_id = _ingest_and_process(client, squad="SQUAD-04")

    body = client.get(f"/api/v1/workflows/{workflow_id}").json()
    assert body["jira_issue_key"]
    assert body["jira_issue_url"] is None


def test_unknown_event_type_yields_empty_detail(client: TestClient, db_session) -> None:
    from app.repositories.workflows import _timeline_event
    from app.repositories.schema import AuditLogRow
    from datetime import datetime, timezone

    row = AuditLogRow(
        id=uuid.uuid4(),
        workflow_execution_id=None,
        internal_correlation_id=uuid.uuid4(),
        event_type="algo.novo",
        details_json='{"subject": "vazou?"}',
        created_at=datetime.now(timezone.utc),
    )
    event = _timeline_event(row)
    assert event.detail == {}
