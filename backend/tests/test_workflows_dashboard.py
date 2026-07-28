"""Tests for the dashboard read endpoints and reprocess (Bloco 1, Task 1.1)."""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.integrations.jira import FakeJiraClient, JiraClientError
from tests.conftest import synthetic_ticket


def _ingest_and_process(client: TestClient, **kwargs) -> dict:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(**kwargs))
    processed = client.post("/api/v1/workflows/process-next")
    return processed.json()


# ---------------------------------------------------------------------------
# GET /api/v1/workflows
# ---------------------------------------------------------------------------


def test_list_workflows_returns_expected_shape(client: TestClient) -> None:
    _ingest_and_process(client, squad="SQUAD-04")

    response = client.get("/api/v1/workflows")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    item = body["items"][0]
    assert set(item.keys()) == {
        "workflow_execution_id",
        "internal_correlation_id",
        "status",
        "attempt_count",
        "squad_id",
        "routing_confidence",
        "routing_rule_version",
        "needs_human_review",
        "last_error",
        "jira_issue_key",
        "link_origin",
        "ticket",
        "updated_at",
    }
    assert set(item["ticket"].keys()) == {"source_ticket_id", "subject", "category", "priority"}
    assert item["status"] == "completed"
    assert item["jira_issue_key"] == "SQD-123"
    assert item["link_origin"] == "deterministic"


def test_list_workflows_never_leaks_requester(client: TestClient) -> None:
    _ingest_and_process(client, squad="SQUAD-04")
    response = client.get("/api/v1/workflows")
    raw = response.text
    assert "requester" not in raw
    assert "user@example.test" not in raw


def test_list_workflows_orders_by_updated_at_desc(client: TestClient) -> None:
    first = _ingest_and_process(client, event_id="evt-a", source_ticket_id="FS-A", squad="SQUAD-04")
    second = _ingest_and_process(client, event_id="evt-b", source_ticket_id="FS-B", squad=None)

    response = client.get("/api/v1/workflows")
    body = response.json()
    ids = [item["workflow_execution_id"] for item in body["items"]]
    assert ids[0] == second["workflow_execution_id"]
    assert ids[1] == first["workflow_execution_id"]


def test_list_workflows_filters_by_status(client: TestClient) -> None:
    _ingest_and_process(client, event_id="evt-a", source_ticket_id="FS-A", squad="SQUAD-04")
    _ingest_and_process(client, event_id="evt-b", source_ticket_id="FS-B", squad=None)

    response = client.get("/api/v1/workflows", params={"status": "needs_human_review"})
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["status"] == "needs_human_review"


def test_list_workflows_rejects_invalid_status(client: TestClient) -> None:
    response = client.get("/api/v1/workflows", params={"status": "bogus"})
    assert response.status_code == 422


def test_list_workflows_limit_default_and_cap(client: TestClient) -> None:
    response = client.get("/api/v1/workflows")
    assert response.status_code == 200

    over_cap = client.get("/api/v1/workflows", params={"limit": 500})
    assert over_cap.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/metrics
# ---------------------------------------------------------------------------


def test_metrics_returns_all_fields(client: TestClient) -> None:
    _ingest_and_process(client, squad="SQUAD-04")

    response = client.get("/api/v1/metrics")
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) == {
        "received",
        "pending",
        "completed",
        "retry_scheduled",
        "failed",
        "needs_human_review",
        "duplicates_avoided",
    }
    assert body["received"] == 1
    assert body["completed"] == 1
    assert body["duplicates_avoided"] is None


# ---------------------------------------------------------------------------
# POST /api/v1/workflows/{id}/reprocess
# ---------------------------------------------------------------------------


def test_reprocess_unknown_id_returns_404(client: TestClient) -> None:
    response = client.post(
        "/api/v1/workflows/00000000-0000-0000-0000-000000000000/reprocess"
    )
    assert response.status_code == 404


def test_reprocess_completed_ticket_returns_409_with_existing_key(client: TestClient) -> None:
    result = _ingest_and_process(client, squad="SQUAD-04")
    workflow_id = result["workflow_execution_id"]

    response = client.post(f"/api/v1/workflows/{workflow_id}/reprocess")
    assert response.status_code == 409
    body = response.json()
    assert body["jira_issue_key"] == "SQD-123"
    assert body["reprocessed"] is False
    assert body["workflow_execution_id"] == workflow_id
    assert body["reason"] == "already_linked"


def test_reprocess_ineligible_status_returns_409_not_eligible(client: TestClient) -> None:
    accepted = client.post(
        "/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04")
    ).json()
    workflow_id = accepted["workflow_execution_id"]
    # Workflow still "pending" — never claimed by the worker, no Jira link.

    response = client.post(f"/api/v1/workflows/{workflow_id}/reprocess")
    assert response.status_code == 409
    body = response.json()
    assert body["reason"] == "not_eligible"
    assert body["jira_issue_key"] is None
    assert body["reprocessed"] is False


def test_reprocess_failed_workflow_reschedules_and_returns_200(
    client: TestClient, fake_jira: FakeJiraClient
) -> None:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))
    fake_jira.raise_error(JiraClientError(retryable=False, message="invalid project"))
    processed = client.post("/api/v1/workflows/process-next").json()
    assert processed["status"] == "failed"
    workflow_id = processed["workflow_execution_id"]

    response = client.post(f"/api/v1/workflows/{workflow_id}/reprocess")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "pending"
    assert body["jira_issue_key"] is None
    assert body["reprocessed"] is True

    # A new outbox event was created — process-next should now succeed
    reprocessed = client.post("/api/v1/workflows/process-next").json()
    assert reprocessed["workflow_execution_id"] == workflow_id
    assert reprocessed["status"] == "completed"


def test_reprocess_twice_never_creates_two_jira_links(
    client: TestClient, fake_jira: FakeJiraClient
) -> None:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))
    fake_jira.raise_error(JiraClientError(retryable=False, message="invalid project"))
    processed = client.post("/api/v1/workflows/process-next").json()
    workflow_id = processed["workflow_execution_id"]

    first = client.post(f"/api/v1/workflows/{workflow_id}/reprocess")
    assert first.status_code == 200

    # Drain the queue — the reprocess-created outbox event completes and
    # persists the Jira link.
    client.post("/api/v1/workflows/process-next")

    second = client.post(f"/api/v1/workflows/{workflow_id}/reprocess")
    assert second.status_code == 409
    assert second.json()["reprocessed"] is False


def test_completed_workflow_has_no_last_error(
    client: TestClient, fake_jira: FakeJiraClient
) -> None:
    """A workflow that failed, then succeeded on reprocess, must not still
    display the stale error on the dashboard — current state is success."""
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))
    fake_jira.raise_error(JiraClientError(retryable=False, message="invalid project"))
    processed = client.post("/api/v1/workflows/process-next").json()
    assert processed["status"] == "failed"
    workflow_id = processed["workflow_execution_id"]

    failed_item = client.get("/api/v1/workflows").json()["items"][0]
    assert failed_item["last_error"] is not None

    client.post(f"/api/v1/workflows/{workflow_id}/reprocess")
    reprocessed = client.post("/api/v1/workflows/process-next").json()
    assert reprocessed["status"] == "completed"

    completed_item = client.get("/api/v1/workflows").json()["items"][0]
    assert completed_item["status"] == "completed"
    assert completed_item["last_error"] is None


def test_exception_queue_distinguishes_the_three_error_categories(
    session_factory, test_settings, test_database_url
) -> None:
    """A rejected credential, a blocked network and a business failure must not
    read the same in the queue — debugging the wrong one is what costs hours."""
    from datetime import datetime, timezone

    import respx

    from app.core.config import Settings
    from app.integrations.freshservice import FreshserviceClient, FreshserviceClientError

    fs_settings = Settings(
        database_url=test_database_url,  # type: ignore[arg-type]
        freshservice_domain="acme.freshservice.com",
        freshservice_api_key="fs-secret-key",  # type: ignore[arg-type]
    )
    client = FreshserviceClient(fs_settings)

    seen = {}
    for http_status in (401, 503, 422):
        with respx.mock:
            respx.get("https://acme.freshservice.com/api/v2/tickets").respond(http_status, json={})
            try:
                client.fetch_updated_since(None)
            except FreshserviceClientError as exc:
                seen[http_status] = str(exc)

    assert seen[401] == "auth:HTTP 401"
    assert seen[503] == "connectivity:HTTP 503"
    assert seen[422] == "business:HTTP 422"
    for message in seen.values():
        assert "fs-secret-key" not in message


def test_queue_never_exposes_ticket_description_or_requester(client: TestClient) -> None:
    """The queue is looked at, screenshotted and pasted into evidence."""
    _ingest_and_process(client, squad=None)

    body = client.get("/api/v1/workflows").json()
    serialized = str(body)
    assert "user@example.test" not in serialized     # requester
    assert "Aplicacao nao responde" not in serialized  # description
