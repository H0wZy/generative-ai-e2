"""Tests for /api/v1/agile — envelope, transition guards and cache."""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes_agile import create_agile_router
from app.core.config import Settings
from app.integrations.jira_agile import AgileUnavailable, FakeJiraAgileClient


@pytest.fixture()
def configured_settings() -> Settings:
    return Settings(
        database_url="postgresql://u:p@localhost:5432/db",  # type: ignore[arg-type]
        jira_base_url="https://example.atlassian.net",  # type: ignore[arg-type]
        jira_email="user@example.test",
        jira_api_token="token",  # type: ignore[arg-type]
        jira_project_key="FRESH",
        jira_board_id=2,
    )


@pytest.fixture()
def agile_client(configured_settings: Settings, fake_agile: FakeJiraAgileClient) -> TestClient:
    app = FastAPI()
    router = create_agile_router(configured_settings)
    app.include_router(router)
    app.dependency_overrides[router.get_client] = lambda: fake_agile
    return TestClient(app)


# ---------------------------------------------------------------------------
# Indisponibilidade
# ---------------------------------------------------------------------------


def test_missing_board_id_returns_200_not_configured(client: TestClient) -> None:
    """A fixture `client` usa test_settings, que não configura o Jira."""
    response = client.get("/api/v1/agile/sprint")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["reason"] == "not_configured"
    assert body["data"] is None


@pytest.mark.parametrize(
    "reason", ["unauthorized", "forbidden", "unavailable", "rate_limited"]
)
def test_jira_failure_returns_200_with_named_reason(
    agile_client: TestClient, fake_agile: FakeJiraAgileClient, reason
) -> None:
    fake_agile.error = AgileUnavailable(reason, "falhou")
    response = agile_client.get("/api/v1/agile/sprint")
    assert response.status_code == 200
    assert response.json()["reason"] == reason


# ---------------------------------------------------------------------------
# Leituras
# ---------------------------------------------------------------------------


def test_sprint_returns_board_sprint_and_blocked(agile_client: TestClient) -> None:
    body = agile_client.get("/api/v1/agile/sprint").json()
    assert body["available"] is True
    data = body["data"]
    assert data["board"]["board_id"] == 2
    assert data["sprint"]["name"] == "FRESH Sprint 1"
    assert data["sprint"]["goal"] is None
    assert [item["key"] for item in data["blocked"]] == ["FRESH-3"]
    # Board sem sprint fechado: velocidade vazia, não gráfico inventado.
    assert data["velocity"] == []


def test_backlog_keeps_rank_and_aggregates_epics(agile_client: TestClient) -> None:
    data = agile_client.get("/api/v1/agile/backlog?limit=5").json()["data"]
    assert [item["rank"] for item in data["items"]] == [1, 2, 3, 4, 5]
    assert len(data["epics"]) == 1
    assert data["epics"][0]["key"] == "FRESH-100"


def test_board_scope_sprint_and_board(agile_client: TestClient) -> None:
    sprint_scope = agile_client.get("/api/v1/agile/board?scope=sprint").json()["data"]
    board_scope = agile_client.get("/api/v1/agile/board?scope=board").json()["data"]
    assert [c["name"] for c in sprint_scope["columns"]] == [
        "A fazer",
        "Fazendo",
        "Em análise",
        "Feito",
    ]
    assert sum(c["count"] for c in board_scope["columns"]) == 3


# ---------------------------------------------------------------------------
# Transição
# ---------------------------------------------------------------------------


def test_target_equal_to_current_status_returns_already_there_without_calling_jira(
    agile_client: TestClient, fake_agile: FakeJiraAgileClient
) -> None:
    """FRESH-2 já está em 'Em análise' — nada é enviado ao Jira."""
    response = agile_client.post(
        "/api/v1/agile/issues/FRESH-2/transition", json={"target_column": "Em análise"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["applied"] is False
    assert body["reason"] == "already_there"
    assert fake_agile.applied == []


def test_successful_transition_returns_status_reread_from_jira(
    agile_client: TestClient, fake_agile: FakeJiraAgileClient
) -> None:
    response = agile_client.post(
        "/api/v1/agile/issues/FRESH-2/transition", json={"target_column": "Feito"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["applied"] is True
    assert body["new_status_name"] == "Feito"
    assert fake_agile.applied == [("FRESH-2", "41")]


def test_unknown_column_returns_409_with_available_transitions(
    agile_client: TestClient,
) -> None:
    response = agile_client.post(
        "/api/v1/agile/issues/FRESH-2/transition", json={"target_column": "Inexistente"}
    )
    assert response.status_code == 409
    body = response.json()
    assert body["reason"] == "no_transition"
    assert body["available_transitions"]


def test_forbidden_transition_returns_403_with_same_envelope(
    agile_client: TestClient, fake_agile: FakeJiraAgileClient
) -> None:
    fake_agile.error = AgileUnavailable("forbidden", "sem permissão")
    response = agile_client.post(
        "/api/v1/agile/issues/FRESH-2/transition", json={"target_column": "Feito"}
    )
    assert response.status_code == 403
    assert response.json()["reason"] == "forbidden"


def test_successful_transition_invalidates_the_read_cache(
    agile_client: TestClient, fake_agile: FakeJiraAgileClient
) -> None:
    before = agile_client.get("/api/v1/agile/board?scope=board").json()["data"]
    assert next(c for c in before["columns"] if c["name"] == "Feito")["count"] == 0

    agile_client.post(
        "/api/v1/agile/issues/FRESH-2/transition", json={"target_column": "Feito"}
    )

    after = agile_client.get("/api/v1/agile/board?scope=board").json()["data"]
    assert next(c for c in after["columns"] if c["name"] == "Feito")["count"] == 1
