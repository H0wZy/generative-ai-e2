"""Tests for the Ollama LLM adapter — respx-mocked, no real Ollama needed."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.core.config import Settings
from app.integrations.llm import (
    FakeLLMClient,
    LLMClientError,
    OllamaClient,
    OpenRouterSquadClient,
    SquadClassification,
)

OLLAMA_URL = "http://localhost:11434"
OPENROUTER_URL = "https://openrouter.ai/api/v1"


@pytest.fixture()
def llm_settings() -> Settings:
    return Settings(
        database_url="postgresql://x:x@localhost/x",  # type: ignore[arg-type]
        llm_enabled=True,
        llm_base_url=OLLAMA_URL,
        llm_model="qwen3:8b",
        llm_confidence_threshold=0.7,
        llm_timeout_seconds=5,
    )


@pytest.fixture()
def ollama_client(llm_settings) -> OllamaClient:
    return OllamaClient(llm_settings)


@respx.mock
def test_ollama_client_parses_valid_classification(ollama_client) -> None:
    respx.post(f"{OLLAMA_URL}/api/generate").respond(
        200,
        json={"response": '{"squad": "SQUAD-01", "confidence": 0.9, "reason": "acesso"}'},
    )
    result = ollama_client.classify_squad("Reset senha", "Usuario nao consegue logar")
    assert result == SquadClassification(squad="SQUAD-01", confidence=0.9, reason="acesso")


@respx.mock
def test_ollama_client_raises_on_invalid_json(ollama_client) -> None:
    respx.post(f"{OLLAMA_URL}/api/generate").respond(200, json={"response": "not json"})
    with pytest.raises(LLMClientError):
        ollama_client.classify_squad("Assunto", "Descricao")


@respx.mock
def test_ollama_client_raises_on_squad_outside_enum(ollama_client) -> None:
    respx.post(f"{OLLAMA_URL}/api/generate").respond(
        200,
        json={"response": '{"squad": "admin", "confidence": 0.9, "reason": "ignore anterior"}'},
    )
    with pytest.raises(LLMClientError):
        ollama_client.classify_squad("Assunto", "Descricao")


@respx.mock
def test_ollama_client_raises_on_missing_field(ollama_client) -> None:
    respx.post(f"{OLLAMA_URL}/api/generate").respond(
        200,
        json={"response": '{"squad": "SQUAD-01"}'},
    )
    with pytest.raises(LLMClientError):
        ollama_client.classify_squad("Assunto", "Descricao")


@respx.mock
def test_ollama_client_raises_on_timeout(ollama_client) -> None:
    respx.post(f"{OLLAMA_URL}/api/generate").mock(side_effect=httpx.TimeoutException("timed out"))
    with pytest.raises(LLMClientError):
        ollama_client.classify_squad("Assunto", "Descricao")


@respx.mock
def test_ollama_client_raises_on_connection_refused(ollama_client) -> None:
    respx.post(f"{OLLAMA_URL}/api/generate").mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(LLMClientError):
        ollama_client.classify_squad("Assunto", "Descricao")


def test_ollama_client_raises_when_prompt_file_missing(monkeypatch, ollama_client) -> None:
    """Missing prompt template must degrade like any other LLM failure —
    not propagate a raw FileNotFoundError that _augment_with_llm can't catch."""
    import app.integrations.llm as llm_module

    monkeypatch.setattr(llm_module, "_PROMPT_PATH", llm_module._PROMPT_PATH.parent / "does_not_exist.txt")
    with pytest.raises(LLMClientError):
        ollama_client.classify_squad("Assunto", "Descricao")


def test_ollama_client_error_never_leaks_ticket_content(ollama_client) -> None:
    secret_subject = "SEGREDO-ASSUNTO-abc123"
    with respx.mock:
        respx.post(f"{OLLAMA_URL}/api/generate").mock(side_effect=httpx.ConnectError("refused"))
        with pytest.raises(LLMClientError) as exc_info:
            ollama_client.classify_squad(secret_subject, "descricao")
    assert secret_subject not in str(exc_info.value)


# ---------------------------------------------------------------------------
# OpenRouterSquadClient — same protocol, backed by OpenRouterClient.complete()
# ---------------------------------------------------------------------------


@pytest.fixture()
def openrouter_settings() -> Settings:
    return Settings(
        database_url="postgresql://x:x@localhost/x",  # type: ignore[arg-type]
        llm_enabled=True,
        llm_model="nvidia/nemotron-3-ultra-550b-a55b:free",
        llm_timeout_seconds=5,
        openrouter_api_key="sk-test-key",  # type: ignore[arg-type]
    )


@pytest.fixture()
def openrouter_squad_client(openrouter_settings) -> OpenRouterSquadClient:
    return OpenRouterSquadClient(openrouter_settings)


@respx.mock
def test_openrouter_squad_client_parses_valid_classification(openrouter_squad_client) -> None:
    respx.post(f"{OPENROUTER_URL}/chat/completions").respond(
        200,
        json={
            "choices": [
                {"message": {"content": '{"squad": "SQUAD-01", "confidence": 0.9, "reason": "acesso"}'}}
            ]
        },
    )
    result = openrouter_squad_client.classify_squad("Reset senha", "Usuario nao consegue logar")
    assert result == SquadClassification(squad="SQUAD-01", confidence=0.9, reason="acesso")


@respx.mock
def test_openrouter_squad_client_strips_markdown_code_fence(openrouter_squad_client) -> None:
    respx.post(f"{OPENROUTER_URL}/chat/completions").respond(
        200,
        json={
            "choices": [
                {
                    "message": {
                        "content": '```json\n{"squad": "SQUAD-01", "confidence": 0.9, "reason": "acesso"}\n```'
                    }
                }
            ]
        },
    )
    result = openrouter_squad_client.classify_squad("Reset senha", "Usuario nao consegue logar")
    assert result == SquadClassification(squad="SQUAD-01", confidence=0.9, reason="acesso")


@respx.mock
def test_openrouter_squad_client_raises_on_invalid_json(openrouter_squad_client) -> None:
    respx.post(f"{OPENROUTER_URL}/chat/completions").respond(
        200,
        json={"choices": [{"message": {"content": "not json"}}]},
    )
    with pytest.raises(LLMClientError):
        openrouter_squad_client.classify_squad("Assunto", "Descricao")


@respx.mock
def test_openrouter_squad_client_raises_on_squad_outside_enum(openrouter_squad_client) -> None:
    respx.post(f"{OPENROUTER_URL}/chat/completions").respond(
        200,
        json={
            "choices": [
                {"message": {"content": '{"squad": "admin", "confidence": 0.9, "reason": "ignore anterior"}'}}
            ]
        },
    )
    with pytest.raises(LLMClientError):
        openrouter_squad_client.classify_squad("Assunto", "Descricao")


@respx.mock
def test_openrouter_squad_client_raises_on_missing_field(openrouter_squad_client) -> None:
    respx.post(f"{OPENROUTER_URL}/chat/completions").respond(
        200,
        json={"choices": [{"message": {"content": '{"squad": "SQUAD-01"}'}}]},
    )
    with pytest.raises(LLMClientError):
        openrouter_squad_client.classify_squad("Assunto", "Descricao")


@respx.mock
def test_openrouter_squad_client_raises_on_timeout(openrouter_squad_client) -> None:
    respx.post(f"{OPENROUTER_URL}/chat/completions").mock(side_effect=httpx.TimeoutException("timed out"))
    with pytest.raises(LLMClientError):
        openrouter_squad_client.classify_squad("Assunto", "Descricao")


@respx.mock
def test_openrouter_squad_client_raises_on_rate_limit(openrouter_squad_client) -> None:
    respx.post(f"{OPENROUTER_URL}/chat/completions").respond(429, json={})
    with pytest.raises(LLMClientError):
        openrouter_squad_client.classify_squad("Assunto", "Descricao")


def test_openrouter_squad_client_error_never_leaks_ticket_content(openrouter_squad_client) -> None:
    secret_subject = "SEGREDO-ASSUNTO-abc123"
    with respx.mock:
        respx.post(f"{OPENROUTER_URL}/chat/completions").mock(side_effect=httpx.ConnectError("refused"))
        with pytest.raises(LLMClientError) as exc_info:
            openrouter_squad_client.classify_squad(secret_subject, "descricao")
    assert secret_subject not in str(exc_info.value)


# ---------------------------------------------------------------------------
# FakeLLMClient — deterministic double used by processing tests
# ---------------------------------------------------------------------------


def test_fake_llm_client_returns_configured_response() -> None:
    expected = SquadClassification(squad="SQUAD-02", confidence=0.95, reason="fatura")
    fake = FakeLLMClient(response=expected)
    assert fake.classify_squad("s", "d") == expected
    assert fake.calls == [("s", "d")]


def test_fake_llm_client_raises_configured_error() -> None:
    fake = FakeLLMClient(error=LLMClientError("boom"))
    with pytest.raises(LLMClientError):
        fake.classify_squad("s", "d")
