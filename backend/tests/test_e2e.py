"""End-to-end test using the JSON fixture — ingest + worker in sequence."""
from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient


def test_fixture_ingests_then_worker_creates_expected_jira_link(
    client: TestClient,
    fixture_payload: dict,
) -> None:
    accepted = client.post("/api/v1/tickets/ingest", json=fixture_payload)
    assert accepted.status_code == 202
    assert UUID(accepted.json()["internal_correlation_id"])
    assert accepted.json()["status"] == "accepted"

    processed = client.post("/api/v1/workflows/process-next")
    assert processed.status_code == 200
    body = processed.json()
    assert body["status"] == "completed"
    assert body["jira_issue_key"] == "PLAT-123"
    assert int(body["attempt_count"]) == 1


def test_duplicate_fixture_reuses_existing_workflow(
    client: TestClient,
    fixture_payload: dict,
) -> None:
    first = client.post("/api/v1/tickets/ingest", json=fixture_payload)
    second = client.post("/api/v1/tickets/ingest", json=fixture_payload)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["status"] == "duplicate"
    assert second.json()["workflow_execution_id"] == first.json()["workflow_execution_id"]
