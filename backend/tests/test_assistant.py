"""Tests for POST /assistant/ask — status fechado, corte de grounding, vazamento."""
from __future__ import annotations

import pytest
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


def _settings(enabled: bool) -> Settings:
    return Settings(
        database_url="postgresql://u:p@localhost:5432/db",  # type: ignore[arg-type]
        assistant_enabled=enabled,
        openrouter_api_key=_KEY if enabled else None,  # type: ignore[arg-type]
        assistant_model=_MODEL,
        assistant_base_url=_PROVIDER_URL,
    )


def _client(
    enabled: bool,
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    session_factory: sessionmaker[Session],
) -> TestClient:
    app = FastAPI()
    router = create_assistant_router(_settings(enabled), session_factory)
    app.include_router(router)
    app.dependency_overrides[router.get_rag_client] = lambda: fake_rag
    app.dependency_overrides[router.get_model_client] = lambda: fake_assistant
    return TestClient(app)


@pytest.fixture()
def assistant_client(
    fake_rag, fake_assistant, session_factory: sessionmaker[Session]
) -> TestClient:
    return _client(True, fake_rag, fake_assistant, session_factory)


def _ask(client: TestClient, question: str = "Como funciona a idempotência?", **kwargs):
    return client.post("/api/v1/assistant/ask", json={"question": question, **kwargs})


# ---------------------------------------------------------------------------
# Caminho feliz e corte
# ---------------------------------------------------------------------------


def test_answered_carries_answer_and_sources(assistant_client: TestClient) -> None:
    body = _ask(assistant_client).json()
    assert body["status"] == "answered"
    assert body["answer"]
    assert len(body["sources"]) == 1
    assert body["truncated_history"] is False


def test_empty_retrieval_still_answers_from_general_knowledge(
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    session_factory: sessionmaker[Session],
) -> None:
    """FR-038: busca vazia não bloqueia — o modelo responde sem trecho para citar."""
    fake_rag.results = []
    body = _ask(_client(True, fake_rag, fake_assistant, session_factory)).json()

    assert body["status"] == "answered"
    assert body["answer"]
    assert body["sources"] == []
    assert len(fake_assistant.calls) == 1


def test_rag_down_still_answers_without_sources(
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    session_factory: sessionmaker[Session],
) -> None:
    """Busca fora do ar também não bloqueia — mesmo caminho de busca vazia."""
    from app.integrations.rag_search import RagUnavailable

    fake_rag.failure = RagUnavailable("conexão recusada")
    body = _ask(_client(True, fake_rag, fake_assistant, session_factory)).json()

    assert body["status"] == "answered"
    assert body["answer"]
    assert body["sources"] == []
    assert len(fake_assistant.calls) == 1


def test_disabled_returns_disabled_without_touching_rag_or_model(
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    session_factory: sessionmaker[Session],
) -> None:
    body = _ask(_client(False, fake_rag, fake_assistant, session_factory)).json()

    assert body["status"] == "disabled"
    assert body["sources"] == []
    assert fake_rag.calls == []
    assert fake_assistant.calls == []


# ---------------------------------------------------------------------------
# Falhas do provedor — FR-043
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("failure", ["rate_limited", "unavailable", "timeout"])
def test_provider_failure_keeps_sources(
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    failure: str,
    session_factory: sessionmaker[Session],
) -> None:
    fake_assistant.failure = failure
    body = _ask(_client(True, fake_rag, fake_assistant, session_factory)).json()

    assert body["status"] == failure
    assert body["answer"] is None
    # A recuperação funcionou: o usuário ainda recebe os trechos.
    assert len(body["sources"]) == 1


# ---------------------------------------------------------------------------
# Vazamento
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("failure", [None, "rate_limited", "unavailable", "timeout"])
def test_response_never_carries_key_model_or_provider_url(
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    failure,
    session_factory: sessionmaker[Session],
) -> None:
    fake_assistant.failure = failure
    raw = _ask(_client(True, fake_rag, fake_assistant, session_factory)).text

    assert _KEY not in raw
    assert _MODEL not in raw
    assert "openrouter" not in raw.lower()


def test_prompt_wraps_each_source_and_is_never_returned(
    assistant_client: TestClient, fake_assistant: FakeAssistantClient
) -> None:
    body = _ask(assistant_client).json()
    _, user_prompt = fake_assistant.calls[0]

    assert "<untrusted_document" in user_prompt
    assert "</untrusted_document>" in user_prompt
    # A resposta nunca devolve o prompt enviado.
    assert "untrusted_document" not in str(body["answer"])


def test_ticket_text_is_redacted_before_leaving_the_process(
    assistant_client: TestClient, fake_assistant: FakeAssistantClient
) -> None:
    _ask(assistant_client, question="Erro do usuário maria@empresa.com no chamado")
    _, user_prompt = fake_assistant.calls[0]

    assert "maria@empresa.com" not in user_prompt
    assert "[email]" in user_prompt


# ---------------------------------------------------------------------------
# Validação
# ---------------------------------------------------------------------------


def test_empty_question_is_422(assistant_client: TestClient) -> None:
    assert _ask(assistant_client, question="").status_code == 422


def test_question_over_2000_chars_is_422(assistant_client: TestClient) -> None:
    assert _ask(assistant_client, question="a" * 2001).status_code == 422


def test_long_history_is_truncated_and_flagged(
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    session_factory: sessionmaker[Session],
) -> None:
    history = [
        {"role": "user" if i % 2 == 0 else "assistant", "text": "x" * 900}
        for i in range(20)
    ]
    client = _client(True, fake_rag, fake_assistant, session_factory)
    body = _ask(client, history=history).json()

    assert body["status"] == "answered"
    assert body["truncated_history"] is True


# ---------------------------------------------------------------------------
# Guardrail: alucinação de tool-call (modelo free tier não tem tools de
# verdade, mas às vezes finge ter — achado de QA em 2026-07-30)
# ---------------------------------------------------------------------------


def test_hallucinated_tool_call_json_is_stripped_from_answer(
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    session_factory: sessionmaker[Session],
) -> None:
    fake_assistant.reply = (
        'Vou buscar isso[{"tool": "grep", "args": {"pattern": "idempotent"}}]'
        "A idempotência garante que reprocessar não duplique."
    )
    client = _client(True, fake_rag, fake_assistant, session_factory)

    body = _ask(client).json()

    assert '"tool"' not in body["answer"]
    assert "A idempotência garante que reprocessar não duplique." in body["answer"]


def test_hallucinated_tool_call_tag_is_stripped_from_answer(
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    session_factory: sessionmaker[Session],
) -> None:
    fake_assistant.reply = "<tool_call>algo aqui</tool_call>Resposta de verdade."
    client = _client(True, fake_rag, fake_assistant, session_factory)

    body = _ask(client).json()

    assert "tool_call" not in body["answer"]
    assert "Resposta de verdade." in body["answer"]


def test_answer_that_is_only_artifact_falls_back_to_original_text(
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    session_factory: sessionmaker[Session],
) -> None:
    fake_assistant.reply = '[{"tool": "grep", "args": {}}]'
    client = _client(True, fake_rag, fake_assistant, session_factory)

    body = _ask(client).json()

    # Nunca devolve resposta vazia — cai pro texto original em vez de sumir.
    assert body["answer"]
