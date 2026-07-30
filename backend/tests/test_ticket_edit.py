"""Tests for PATCH /workflows/{id}/ticket — edit while the ticket is open."""
from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from tests.conftest import synthetic_ticket


def _ingest_and_process(client: TestClient, **kwargs) -> str:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(**kwargs))
    client.post("/api/v1/workflows/process-next")
    return client.get("/api/v1/workflows").json()["items"][0]["workflow_execution_id"]


def test_patch_updates_only_sent_fields(client: TestClient) -> None:
    workflow_id = _ingest_and_process(client, squad="SQUAD-04")

    response = client.patch(
        f"/api/v1/workflows/{workflow_id}/ticket",
        json={"subject": "Impressora sem toner — atualizado", "priority": "urgent"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["ticket"]["subject"] == "Impressora sem toner — atualizado"
    assert body["ticket"]["priority"] == "urgent"
    # category não foi enviado — permanece o valor original do ingest.
    assert body["ticket"]["category"] == "incident"


def test_patch_unknown_workflow_returns_404(client: TestClient) -> None:
    response = client.patch(
        f"/api/v1/workflows/{uuid.uuid4()}/ticket",
        json={"subject": "não importa"},
    )

    assert response.status_code == 404


def test_patch_resolved_ticket_returns_409(client: TestClient) -> None:
    workflow_id = _ingest_and_process(client, squad="SQUAD-04")
    client.post(f"/api/v1/workflows/{workflow_id}/resolve")

    response = client.patch(
        f"/api/v1/workflows/{workflow_id}/ticket",
        json={"subject": "tentativa depois de concluído"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "chamado já concluído"}
