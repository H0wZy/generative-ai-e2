"""Ollama LLM adapter for ambiguous squad classification.

``OllamaClient`` talks to a local Ollama server via HTTPX.
``FakeLLMClient`` is deterministic and used in tests — no network calls.
Both share the ``LLMClientProtocol`` interface.

The ticket subject/description is untrusted input: it is placed inside a
delimited block in the prompt, never concatenated into an error message.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import httpx
from pydantic import BaseModel, ValidationError, field_validator

from app.core.config import Settings
from app.domain.squads import SQUADS, normalize_squad
from app.integrations.openrouter import AssistantFailure, OpenRouterClient

KNOWN_SQUADS = set(SQUADS)

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "squad_classifier_v2.txt"
PROMPT_VERSION = "squad_classifier_v2"


class SquadClassification(BaseModel):
    """Model output. ``squad`` is validated against the closed enum.

    A value outside the enum — including one a ticket tried to inject — fails
    validation, which the caller turns into human review.
    """

    squad: str
    confidence: float
    reason: str

    @field_validator("squad")
    @classmethod
    def _squad_in_enum(cls, value: str) -> str:
        if value == "unknown":
            return value
        canonical = normalize_squad(value)
        if canonical is None:
            raise ValueError("squad outside the closed enum")
        return canonical


class LLMClientError(Exception):
    """Any classification failure — connection, timeout, malformed output.

    The message is always a static description; it must never include the
    ticket subject/description or the model's raw response.
    """


class LLMClientProtocol(Protocol):
    def classify_squad(self, subject: str, description: str) -> SquadClassification: ...


class OllamaClient:
    """Real adapter — calls a local Ollama server's ``/api/generate``."""

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.llm_base_url.rstrip("/")
        self._model = settings.llm_model
        self._timeout = settings.llm_timeout_seconds

    def classify_squad(self, subject: str, description: str) -> SquadClassification:
        try:
            prompt = _PROMPT_PATH.read_text().format(subject=subject, description=description)
            with httpx.Client(timeout=self._timeout) as client:
                response = client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": prompt,
                        "stream": False,
                        "format": "json",
                    },
                )
                response.raise_for_status()
                raw = response.json()["response"]
                data = json.loads(raw)
                return SquadClassification.model_validate(data)
        except httpx.HTTPError:
            raise LLMClientError("llm request failed") from None
        except OSError:
            raise LLMClientError("llm prompt template unavailable") from None
        except (KeyError, json.JSONDecodeError, ValidationError):
            raise LLMClientError("llm returned an invalid response") from None


_JSON_SYSTEM_PROMPT = (
    "Responda APENAS com um objeto JSON válido, sem texto antes ou depois, "
    'no formato {"squad": ..., "confidence": ..., "reason": ...}.'
)


class OpenRouterSquadClient:
    """Real adapter — classifies via OpenRouter, reusing ``OpenRouterClient``."""

    def __init__(self, settings: Settings) -> None:
        self._client = OpenRouterClient(
            base_url=settings.assistant_base_url,
            api_key=settings.openrouter_api_key.get_secret_value() if settings.openrouter_api_key else "",
            model=settings.llm_model,
            timeout_seconds=settings.llm_timeout_seconds,
        )

    def classify_squad(self, subject: str, description: str) -> SquadClassification:
        try:
            prompt = _PROMPT_PATH.read_text().format(subject=subject, description=description)
            raw = self._client.complete(_JSON_SYSTEM_PROMPT, prompt)
            raw = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
            data = json.loads(raw)
            return SquadClassification.model_validate(data)
        except AssistantFailure:
            raise LLMClientError("llm request failed") from None
        except OSError:
            raise LLMClientError("llm prompt template unavailable") from None
        except (json.JSONDecodeError, ValidationError):
            raise LLMClientError("llm returned an invalid response") from None


def resolve_squad(result: SquadClassification, threshold: float) -> tuple[str | None, bool]:
    """Apply the confidence threshold to a classification.

    Returns ``(squad_id, needs_human_review)``. Shared by ``ProcessingService``
    and the offline eval script so both apply the exact same rule.
    """
    confident = result.squad in KNOWN_SQUADS and result.confidence >= threshold
    return (result.squad if confident else None, not confident)


@dataclass
class FakeLLMClient:
    """Deterministic double — returns a configured response or raises."""

    response: SquadClassification | None = None
    error: LLMClientError | None = None
    calls: list[tuple[str, str]] = field(default_factory=list)

    def classify_squad(self, subject: str, description: str) -> SquadClassification:
        self.calls.append((subject, description))
        if self.error is not None:
            raise self.error
        if self.response is not None:
            return self.response
        return SquadClassification(squad="unknown", confidence=0.0, reason="fake default")
