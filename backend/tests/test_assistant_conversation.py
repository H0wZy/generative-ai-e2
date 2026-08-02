"""Tests for /assistant/conversations* and conversation-scoped persistence.

FR-058/FR-059: histórico por sessão, isolado por `X-Session-Id`, sem login.
Uma sessão pode ter várias conversas nomeadas (não mais uma única).
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


def test_list_conversations_without_header_is_empty_not_404(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.get("/api/v1/assistant/conversations")

    assert response.status_code == 200
    assert response.json() == {"conversations": []}


def test_list_conversations_with_malformed_header_is_also_empty(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.get(
        "/api/v1/assistant/conversations", headers={"X-Session-Id": "not-a-uuid"}
    )

    assert response.status_code == 200
    assert response.json() == {"conversations": []}


def test_create_conversation_without_session_header_is_rejected(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.post("/api/v1/assistant/conversations")

    assert response.status_code == 400


def test_create_then_list_then_fetch_messages(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    created = client.post(
        "/api/v1/assistant/conversations", headers={"X-Session-Id": _SESSION_A}
    ).json()
    assert created["title"] == ""
    conversation_id = created["id"]

    ask_response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Como funciona a idempotência?", "conversation_id": conversation_id},
        headers={"X-Session-Id": _SESSION_A},
    )
    assert ask_response.status_code == 200
    answered = ask_response.json()

    listed = client.get(
        "/api/v1/assistant/conversations", headers={"X-Session-Id": _SESSION_A}
    ).json()["conversations"]
    assert len(listed) == 1
    # Título vira o começo da primeira pergunta (best-effort, sem tag/IA envolvida).
    assert listed[0]["title"] == "Como funciona a idempotência?"

    messages = client.get(
        f"/api/v1/assistant/conversations/{conversation_id}/messages",
        headers={"X-Session-Id": _SESSION_A},
    ).json()["messages"]
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["text"] == "Como funciona a idempotência?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["text"] == answered["answer"]


def test_unknown_conversation_id_is_404(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.get(
        "/api/v1/assistant/conversations/00000000-0000-0000-0000-000000000000/messages",
        headers={"X-Session-Id": _SESSION_A},
    )

    assert response.status_code == 404


def test_session_b_cannot_read_session_a_conversation(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    created = client.post(
        "/api/v1/assistant/conversations", headers={"X-Session-Id": _SESSION_A}
    ).json()

    response = client.get(
        f"/api/v1/assistant/conversations/{created['id']}/messages",
        headers={"X-Session-Id": _SESSION_B},
    )

    assert response.status_code == 404

    listed_b = client.get(
        "/api/v1/assistant/conversations", headers={"X-Session-Id": _SESSION_B}
    ).json()["conversations"]
    assert listed_b == []


def test_two_conversations_in_same_session_stay_independent(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}

    first = client.post("/api/v1/assistant/conversations", headers=headers).json()
    second = client.post("/api/v1/assistant/conversations", headers=headers).json()

    client.post(
        "/api/v1/assistant/ask",
        json={"question": "Pergunta da primeira conversa", "conversation_id": first["id"]},
        headers=headers,
    )
    client.post(
        "/api/v1/assistant/ask",
        json={"question": "Pergunta da segunda conversa", "conversation_id": second["id"]},
        headers=headers,
    )

    first_messages = client.get(
        f"/api/v1/assistant/conversations/{first['id']}/messages", headers=headers
    ).json()["messages"]
    second_messages = client.get(
        f"/api/v1/assistant/conversations/{second['id']}/messages", headers=headers
    ).json()["messages"]

    assert all(m["text"] != "Pergunta da segunda conversa" for m in first_messages)
    assert all(m["text"] != "Pergunta da primeira conversa" for m in second_messages)


# Favoritar (pin), renomear e excluir conversa — menu de contexto da sidebar
# (achado de QA em 2026-07-31).


def test_rename_conversation(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}
    created = client.post("/api/v1/assistant/conversations", headers=headers).json()

    response = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"title": "Título renomeado"},
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json()["title"] == "Título renomeado"


def test_rename_conversation_with_blank_title_is_422(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}
    created = client.post("/api/v1/assistant/conversations", headers=headers).json()

    response = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"title": "   "},
        headers=headers,
    )

    assert response.status_code == 422


def test_favorite_conversation_sorts_before_recent(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}

    older = client.post("/api/v1/assistant/conversations", headers=headers).json()
    newer = client.post("/api/v1/assistant/conversations", headers=headers).json()

    # `newer` foi criada por último, então normalmente viria primeiro — favoritar
    # `older` deve furar a fila mesmo sendo mais antiga.
    favorited = client.patch(
        f"/api/v1/assistant/conversations/{older['id']}",
        json={"is_favorite": True},
        headers=headers,
    )
    assert favorited.status_code == 200
    assert favorited.json()["is_favorite"] is True

    listed = client.get("/api/v1/assistant/conversations", headers=headers).json()["conversations"]
    assert listed[0]["id"] == older["id"]
    assert listed[1]["id"] == newer["id"]


def test_session_b_cannot_rename_or_favorite_or_delete_session_a_conversation(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    created = client.post(
        "/api/v1/assistant/conversations", headers={"X-Session-Id": _SESSION_A}
    ).json()
    other_headers = {"X-Session-Id": _SESSION_B}

    rename = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"title": "Sequestro"},
        headers=other_headers,
    )
    favorite = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_favorite": True},
        headers=other_headers,
    )
    delete = client.delete(
        f"/api/v1/assistant/conversations/{created['id']}", headers=other_headers
    )

    assert rename.status_code == 404
    assert favorite.status_code == 404
    assert delete.status_code == 404


def test_delete_conversation_removes_it_and_its_messages(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}
    created = client.post("/api/v1/assistant/conversations", headers=headers).json()
    client.post(
        "/api/v1/assistant/ask",
        json={"question": "Pergunta antes de excluir", "conversation_id": created["id"]},
        headers=headers,
    )

    response = client.delete(f"/api/v1/assistant/conversations/{created['id']}", headers=headers)
    assert response.status_code == 204

    listed = client.get("/api/v1/assistant/conversations", headers=headers).json()["conversations"]
    assert listed == []

    messages = client.get(
        f"/api/v1/assistant/conversations/{created['id']}/messages", headers=headers
    )
    assert messages.status_code == 404


def test_delete_unknown_conversation_is_404(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.delete(
        "/api/v1/assistant/conversations/00000000-0000-0000-0000-000000000000",
        headers={"X-Session-Id": _SESSION_A},
    )

    assert response.status_code == 404


def test_ask_without_conversation_id_still_answers_but_does_not_persist(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.post(
        "/api/v1/assistant/ask",
        json={"question": "Pergunta sem conversa"},
        headers={"X-Session-Id": _SESSION_A},
    )

    assert response.status_code == 200
    listed = client.get(
        "/api/v1/assistant/conversations", headers={"X-Session-Id": _SESSION_A}
    ).json()["conversations"]
    assert listed == []


# ---------------------------------------------------------------------------
# Arquivamento (specs/007) — `archived_at` nulável, escrito só pelo servidor.
# ---------------------------------------------------------------------------


def _ids(client: TestClient, headers: dict[str, str], state: str | None = None) -> list[str]:
    params = {"state": state} if state else None
    listed = client.get(
        "/api/v1/assistant/conversations", headers=headers, params=params
    ).json()["conversations"]
    return [conversation["id"] for conversation in listed]


def test_archive_moves_conversation_between_lists(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}
    created = client.post("/api/v1/assistant/conversations", headers=headers).json()

    assert created["archived_at"] is None

    archived = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_archived": True},
        headers=headers,
    )

    assert archived.status_code == 200
    assert archived.json()["archived_at"] is not None
    assert _ids(client, headers) == []
    assert _ids(client, headers, "archived") == [created["id"]]


def test_unarchive_restores_conversation_with_favorite_intact(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}
    created = client.post("/api/v1/assistant/conversations", headers=headers).json()
    client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_favorite": True},
        headers=headers,
    )
    client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_archived": True},
        headers=headers,
    )

    restored = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_archived": False},
        headers=headers,
    )

    assert restored.status_code == 200
    assert restored.json()["archived_at"] is None
    # Arquivar não é uma forma de desfavoritar — desarquivar devolve a conversa
    # exatamente à lista de onde ela saiu (FR-011).
    assert restored.json()["is_favorite"] is True
    assert _ids(client, headers) == [created["id"]]
    assert _ids(client, headers, "archived") == []


def test_archiving_a_favorite_keeps_it_favorite(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}
    created = client.post("/api/v1/assistant/conversations", headers=headers).json()
    client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_favorite": True},
        headers=headers,
    )

    archived = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_archived": True},
        headers=headers,
    )

    assert archived.json()["is_favorite"] is True


def test_archiving_twice_keeps_the_first_timestamp(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}
    created = client.post("/api/v1/assistant/conversations", headers=headers).json()

    first = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_archived": True},
        headers=headers,
    ).json()["archived_at"]
    second = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_archived": True},
        headers=headers,
    ).json()["archived_at"]

    # FR-012 registra QUANDO foi arquivada, não quando o botão foi clicado pela
    # última vez.
    assert first == second


def test_archiving_does_not_touch_updated_at(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}
    created = client.post("/api/v1/assistant/conversations", headers=headers).json()

    archived = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_archived": True},
        headers=headers,
    ).json()
    restored = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_archived": False},
        headers=headers,
    ).json()

    # `updated_at` significa "última atividade da conversa" e ordena "Recentes".
    # Arquivar não é atividade: desarquivar tem que devolver a conversa à
    # posição que ela tinha.
    assert archived["updated_at"] == created["updated_at"]
    assert restored["updated_at"] == created["updated_at"]


def test_session_b_cannot_archive_session_a_conversation(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    created = client.post(
        "/api/v1/assistant/conversations", headers={"X-Session-Id": _SESSION_A}
    ).json()

    response = client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_archived": True},
        headers={"X-Session-Id": _SESSION_B},
    )

    assert response.status_code == 404
    assert _ids(client, {"X-Session-Id": _SESSION_A}) == [created["id"]]


def test_listing_without_state_hides_archived(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}
    kept = client.post("/api/v1/assistant/conversations", headers=headers).json()
    hidden = client.post("/api/v1/assistant/conversations", headers=headers).json()
    client.patch(
        f"/api/v1/assistant/conversations/{hidden['id']}",
        json={"is_archived": True},
        headers=headers,
    )

    # Sem `state`, o comportamento é o de antes desta rodada — quem já consome
    # a rota não precisa mudar nada pra deixar de ver arquivadas (FR-009).
    assert _ids(client, headers) == [kept["id"]]


def test_delete_archived_conversation_works_like_an_active_one(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    headers = {"X-Session-Id": _SESSION_A}
    created = client.post("/api/v1/assistant/conversations", headers=headers).json()
    client.patch(
        f"/api/v1/assistant/conversations/{created['id']}",
        json={"is_archived": True},
        headers=headers,
    )

    response = client.delete(f"/api/v1/assistant/conversations/{created['id']}", headers=headers)

    assert response.status_code == 204
    assert _ids(client, headers, "archived") == []


def test_unknown_state_value_is_422(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.get(
        "/api/v1/assistant/conversations",
        headers={"X-Session-Id": _SESSION_A},
        params={"state": "todas"},
    )

    assert response.status_code == 422
