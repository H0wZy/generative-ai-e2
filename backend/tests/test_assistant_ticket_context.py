"""Tests for the assistant's ticket-context heuristic (FR-060).

Chave Jira citada na pergunta -> `ticket_context` preenchido. Chave
inexistente ou pergunta sem chave -> `ticket_context: null`, nunca erro.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes import create_router
from app.api.routes_assistant import create_assistant_router
from app.core.config import Settings
from app.integrations.jira import FakeJiraClient
from app.integrations.openrouter import FakeAssistantClient
from app.integrations.rag_search import FakeRagSearchClient
from tests.conftest import synthetic_ticket

_KEY = "sk-or-chave-secreta-de-teste"
_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
_PROVIDER_URL = "https://openrouter.ai/api/v1"


def _settings(test_database_url: str) -> Settings:
    return Settings(
        database_url=test_database_url,  # type: ignore[arg-type]
        jira_base_url=None,
        jira_project_key="SQD",
        assistant_enabled=True,
        openrouter_api_key=_KEY,  # type: ignore[arg-type]
        assistant_model=_MODEL,
        assistant_base_url=_PROVIDER_URL,
    )


def _client(
    test_database_url: str,
    session_factory: sessionmaker[Session],
    fake_jira: FakeJiraClient,
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> TestClient:
    settings = _settings(test_database_url)
    app = FastAPI()

    itsm_router = create_router(settings, session_factory)
    app.include_router(itsm_router)
    app.dependency_overrides[itsm_router.get_jira_client] = lambda: fake_jira

    assistant_router = create_assistant_router(settings, session_factory)
    app.include_router(assistant_router)
    app.dependency_overrides[assistant_router.get_rag_client] = lambda: fake_rag
    app.dependency_overrides[assistant_router.get_model_client] = lambda: fake_assistant

    return TestClient(app)


def _create_linked_ticket(client: TestClient) -> str:
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))
    client.post("/api/v1/workflows/process-next")
    items = client.get("/api/v1/workflows").json()["items"]
    return items[0]["jira_issue_key"]


def test_question_with_existing_key_fills_ticket_context(
    test_database_url: str,
    session_factory: sessionmaker[Session],
    fake_jira: FakeJiraClient,
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(test_database_url, session_factory, fake_jira, fake_rag, fake_assistant)
    jira_key = _create_linked_ticket(client)

    body = client.post(
        "/api/v1/assistant/ask", json={"question": f"Qual o status do {jira_key}?"}
    ).json()

    assert body["ticket_context"] == {
        "jira_issue_key": jira_key,
        "status": "completed",
        "subject": "Servico indisponivel",
        "squad_id": "SQUAD-04",
    }


def test_question_with_unknown_key_returns_null_context_without_error(
    test_database_url: str,
    session_factory: sessionmaker[Session],
    fake_jira: FakeJiraClient,
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(test_database_url, session_factory, fake_jira, fake_rag, fake_assistant)

    response = client.post(
        "/api/v1/assistant/ask", json={"question": "Qual o status do FRESH-999?"}
    )

    assert response.status_code == 200
    assert response.json()["ticket_context"] is None


def test_question_without_key_never_queries_the_workflow_repository(
    test_database_url: str,
    session_factory: sessionmaker[Session],
    fake_jira: FakeJiraClient,
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    monkeypatch,
) -> None:
    client = _client(test_database_url, session_factory, fake_jira, fake_rag, fake_assistant)

    from app.repositories.workflows import WorkflowRepository

    def _fail(self, jira_issue_key: str):
        raise AssertionError("find_by_jira_key não deveria ser chamado sem chave na pergunta")

    monkeypatch.setattr(WorkflowRepository, "find_by_jira_key", _fail)

    body = client.post(
        "/api/v1/assistant/ask", json={"question": "Como funciona a idempotência?"}
    ).json()

    assert body["ticket_context"] is None
