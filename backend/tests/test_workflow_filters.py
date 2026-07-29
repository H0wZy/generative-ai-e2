"""Tests for GET /workflows filters, pagination and reprocess_eligible."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.integrations.jira import FakeJiraClient, JiraClientError
from tests.conftest import synthetic_ticket


def _ingest_and_process(client: TestClient, **kwargs) -> dict:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(**kwargs))
    processed = client.post("/api/v1/workflows/process-next")
    return processed.json()


def test_q_matches_subject_case_insensitive(client: TestClient) -> None:
    _ingest_and_process(client, event_id="evt-a", source_ticket_id="FS-A", squad="SQUAD-04")

    response = client.get("/api/v1/workflows", params={"q": "SERVICO"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["ticket"]["source_ticket_id"] == "FS-A"


def test_q_matches_source_ticket_id(client: TestClient) -> None:
    _ingest_and_process(client, event_id="evt-a", source_ticket_id="FS-A", squad="SQUAD-04")
    _ingest_and_process(client, event_id="evt-b", source_ticket_id="FS-B", squad=None)

    response = client.get("/api/v1/workflows", params={"q": "fs-b"})
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["ticket"]["source_ticket_id"] == "FS-B"


def test_filters_combine(client: TestClient) -> None:
    _ingest_and_process(client, event_id="evt-a", source_ticket_id="FS-A", squad="SQUAD-04")
    _ingest_and_process(client, event_id="evt-b", source_ticket_id="FS-B", squad=None)

    response = client.get(
        "/api/v1/workflows",
        params={"status": "needs_human_review", "priority": "high", "squad": "SQUAD-04"},
    )
    body = response.json()
    # SQUAD-04 workflow is completed, not needs_human_review — combined filter yields none
    assert body["total"] == 0
    assert body["items"] == []


def test_total_reflects_filtered_set_not_page(client: TestClient) -> None:
    for i in range(3):
        _ingest_and_process(client, event_id=f"evt-{i}", source_ticket_id=f"FS-{i}", squad="SQUAD-04")

    response = client.get("/api/v1/workflows", params={"limit": 2})
    body = response.json()
    assert body["total"] == 3
    assert len(body["items"]) == 2


def test_offset_paginates_without_losing_filter(client: TestClient) -> None:
    for i in range(3):
        _ingest_and_process(client, event_id=f"evt-{i}", source_ticket_id=f"FS-{i}", squad="SQUAD-04")

    first_page = client.get("/api/v1/workflows", params={"limit": 2, "offset": 0}).json()
    second_page = client.get("/api/v1/workflows", params={"limit": 2, "offset": 2}).json()

    first_ids = {item["workflow_execution_id"] for item in first_page["items"]}
    second_ids = {item["workflow_execution_id"] for item in second_page["items"]}
    assert first_ids.isdisjoint(second_ids)
    assert len(second_page["items"]) == 1
    assert second_page["total"] == 3


def test_reprocess_eligible_true_for_failed(client: TestClient, fake_jira: FakeJiraClient) -> None:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))
    fake_jira.raise_error(JiraClientError(retryable=False, message="invalid project"))
    client.post("/api/v1/workflows/process-next")

    body = client.get("/api/v1/workflows").json()
    assert body["items"][0]["status"] == "failed"
    assert body["items"][0]["reprocess_eligible"] is True


def test_reprocess_eligible_false_for_completed(client: TestClient) -> None:
    _ingest_and_process(client, squad="SQUAD-04")

    body = client.get("/api/v1/workflows").json()
    assert body["items"][0]["status"] == "completed"
    assert body["items"][0]["reprocess_eligible"] is False


def test_q_over_120_chars_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/workflows", params={"q": "a" * 121})
    assert response.status_code == 422


def test_no_filters_behaves_as_before(client: TestClient) -> None:
    _ingest_and_process(client, squad="SQUAD-04")
    response = client.get("/api/v1/workflows")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
