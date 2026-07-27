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
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, ValidationError

from app.core.config import Settings

KNOWN_SQUADS = {"identity", "finance", "platform"}

_PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "squad_classifier_v1.txt"
PROMPT_VERSION = "squad_classifier_v1"


class SquadClassification(BaseModel):
    squad: Literal["identity", "finance", "platform", "unknown"]
    confidence: float
    reason: str


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
