"""Tests for POST /workflows/{id}/resolve — idempotency (FR-053)."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from tests.conftest import synthetic_ticket


def _ingest_and_process(client: TestClient, **kwargs) -> str:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(**kwargs))
    client.post("/api/v1/workflows/process-next")
    return client.get("/api/v1/workflows").json()["items"][0]["workflow_execution_id"]


def test_resolve_returns_timestamp(client: TestClient) -> None:
    workflow_id = _ingest_and_process(client, squad="SQUAD-04")

    response = client.post(f"/api/v1/workflows/{workflow_id}/resolve")

    assert response.status_code == 200
    body = response.json()
    assert body["workflow_execution_id"] == workflow_id
    assert body["resolved_at"]


def test_resolve_is_idempotent(client: TestClient) -> None:
    workflow_id = _ingest_and_process(client, squad="SQUAD-04")

    first = client.post(f"/api/v1/workflows/{workflow_id}/resolve").json()
    second = client.post(f"/api/v1/workflows/{workflow_id}/resolve").json()

    assert first["resolved_at"] == second["resolved_at"]


def test_resolve_unknown_workflow_returns_404(client: TestClient) -> None:
    response = client.post(f"/api/v1/workflows/{uuid.uuid4()}/resolve")

    assert response.status_code == 404
