"""Tests for GET /assistant/conversation and session-scoped persistence.

FR-058/FR-059: histórico por sessão, isolado por `X-Session-Id`, sem login.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes_assistant import create_assistant_router
from app.core.config import Settings
from app.integrations.openrouter import FakeAssistantClient
from app.integrations.rag_search import FakeRagSearchClient

_KEY = "sk-or-chave-secreta-de-teste"
_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
_PROVIDER_URL = "https://openrouter.ai/api/v1"

_SESSION_A = "11111111-1111-1111-1111-111111111111"
_SESSION_B = "22222222-2222-2222-2222-222222222222"


def _settings() -> Settings:
    return Settings(
        database_url="postgresql://u:p@localhost:5432/db",  # type: ignore[arg-type]
        assistant_enabled=True,
        openrouter_api_key=_KEY,  # type: ignore[arg-type]
        assistant_model=_MODEL,
        assistant_base_url=_PROVIDER_URL,
    )


def _client(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> TestClient:
    app = FastAPI()
    router = create_assistant_router(_settings(), session_factory)
    app.include_router(router)
    app.dependency_overrides[router.get_rag_client] = lambda: fake_rag
    app.dependency_overrides[router.get_model_client] = lambda: fake_assistant
    return TestClient(app)


def test_conversation_without_header_is_empty_not_404(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.get("/api/v1/assistant/conversation")

    assert response.status_code == 200
    assert response.json() == {"messages": []}


def test_conversation_with_malformed_header_is_also_empty(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.get(
        "/api/v1/assistant/conversation", headers={"X-Session-Id": "not-a-uuid"}
    )

    assert response.status_code == 200
    assert response.json() == {"messages": []}


def test_ask_persists_question_and_answer_in_order(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    ask_response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Como funciona a idempotência?"},
        headers={"X-Session-Id": _SESSION_A},
    )
    assert ask_response.status_code == 200
    answered = ask_response.json()

    conversation = client.get(
        "/api/v1/assistant/conversation", headers={"X-Session-Id": _SESSION_A}
    ).json()

    messages = conversation["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["text"] == "Como funciona a idempotência?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["text"] == answered["answer"]


def test_two_sessions_never_see_each_others_history(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    client.post(
        "/api/v1/assistant/ask",
        json={"question": "Pergunta da sessão A"},
        headers={"X-Session-Id": _SESSION_A},
    )
    client.post(
        "/api/v1/assistant/ask",
        json={"question": "Pergunta da sessão B"},
        headers={"X-Session-Id": _SESSION_B},
    )

    conversation_a = client.get(
        "/api/v1/assistant/conversation", headers={"X-Session-Id": _SESSION_A}
    ).json()
    conversation_b = client.get(
        "/api/v1/assistant/conversation", headers={"X-Session-Id": _SESSION_B}
    ).json()

    assert all(m["text"] != "Pergunta da sessão B" for m in conversation_a["messages"])
    assert all(m["text"] != "Pergunta da sessão A" for m in conversation_b["messages"])
    assert conversation_a["messages"][0]["text"] == "Pergunta da sessão A"
    assert conversation_b["messages"][0]["text"] == "Pergunta da sessão B"
