"""Cliente do OpenRouter — Chat Completions compatível com OpenAI.

`httpx` direto, sem SDK: uma chamada POST não justifica dependência nova.

Erro do provedor NUNCA vira mensagem repassada. Vira `AssistantFailure` com
um dos status fechados, e é o serviço que traduz para a resposta (FR-042).
Chave, modelo e URL do provedor não aparecem em exceção nem em log.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import httpx


@dataclass
class AssistantFailure(Exception):
    status: str  # "rate_limited" | "unavailable" | "timeout"

    def __str__(self) -> str:
        return f"AssistantFailure({self.status})"


class AssistantClientProtocol(Protocol):
    def complete(self, system: str, user: str) -> str: ...


class OpenRouterClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: int,
        max_tokens: int | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout_seconds
        self._max_tokens = max_tokens

    def complete(self, system: str, user: str) -> str:
        payload: dict = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if self._max_tokens is not None:
            payload["max_tokens"] = self._max_tokens
        headers = {"Authorization": f"Bearer {self._api_key}"}

        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions", json=payload, headers=headers
                )
        except httpx.TimeoutException as exc:
            raise AssistantFailure("timeout") from exc
        except httpx.HTTPError as exc:
            raise AssistantFailure("unavailable") from exc

        if response.status_code == 429:
            raise AssistantFailure("rate_limited")
        if response.status_code >= 400:
            raise AssistantFailure("unavailable")

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            # Corpo malformado é indisponibilidade do provedor, não erro nosso.
            raise AssistantFailure("unavailable") from exc

        if not isinstance(content, str) or not content.strip():
            raise AssistantFailure("unavailable")
        return content


@dataclass
class FakeAssistantClient:
    """Fake com modos de falha. `failure` sobrepõe a resposta."""

    reply: str = "O worker reivindica um evento por vez, o que garante idempotência."
    failure: str | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)

    def complete(self, system: str, user: str) -> str:
        self.calls.append((system, user))
        if self.failure is not None:
            raise AssistantFailure(self.failure)
        return self.reply
