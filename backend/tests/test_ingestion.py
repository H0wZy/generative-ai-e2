"""Tests for ticket ingestion — idempotency, correlation IDs, validation."""
from __future__ import annotations

from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from tests.conftest import synthetic_ticket


def test_ingest_returns_202_with_uuid_correlation_id(client: TestClient) -> None:
    response = client.post("/api/v1/tickets/ingest", json=synthetic_ticket())
    assert response.status_code == 202
    body = response.json()
    # internal_correlation_id must be a valid UUID
    assert UUID(body["internal_correlation_id"])
    # Must NOT echo the external_correlation_id as the internal one
    assert body["internal_correlation_id"] != "n8n-execution-001"
    assert body["status"] == "accepted"
    assert UUID(body["workflow_execution_id"])


def test_ingest_generates_unique_internal_ids_per_event(client: TestClient) -> None:
    first = client.post("/api/v1/tickets/ingest", json=synthetic_ticket())
    different_event = synthetic_ticket(event_id="evt-002", source_ticket_id="FS-200")
    second = client.post("/api/v1/tickets/ingest", json=different_event)

    assert first.status_code == 202
    assert second.status_code == 202
    assert first.json()["internal_correlation_id"] != second.json()["internal_correlation_id"]
    assert first.json()["workflow_execution_id"] != second.json()["workflow_execution_id"]


def test_same_source_event_returns_duplicate(client: TestClient) -> None:
    ticket = synthetic_ticket()
    first = client.post("/api/v1/tickets/ingest", json=ticket)
    second = client.post("/api/v1/tickets/ingest", json=ticket)

    assert first.status_code == 202
    assert second.status_code == 202
    assert second.json()["status"] == "duplicate"
    assert second.json()["workflow_execution_id"] == first.json()["workflow_execution_id"]
    assert second.json()["internal_correlation_id"] == first.json()["internal_correlation_id"]


def test_ingest_without_external_correlation_id(client: TestClient) -> None:
    ticket = synthetic_ticket(external_correlation_id=None)
    response = client.post("/api/v1/tickets/ingest", json=ticket)
    assert response.status_code == 202
    assert UUID(response.json()["internal_correlation_id"])


def test_ingest_rejects_empty_subject(client: TestClient) -> None:
    ticket = synthetic_ticket()
    ticket["subject"] = ""
    response = client.post("/api/v1/tickets/ingest", json=ticket)
    assert response.status_code == 422


def test_ingest_rejects_invalid_priority(client: TestClient) -> None:
    ticket = synthetic_ticket()
    ticket["priority"] = "critical"
    response = client.post("/api/v1/tickets/ingest", json=ticket)
    assert response.status_code == 422
