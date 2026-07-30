"""Modelos do assistente. `status` é enum fechado — é o que torna FR-043
testável: cada modo de falha tem valor próprio, não string de erro variável.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AssistantStatus = Literal[
    "answered",
    "rate_limited",
    "unavailable",
    "timeout",
    "disabled",
]


class AssistantMessage(BaseModel):
    role: Literal["user", "assistant"]
    text: str = Field(max_length=8000)


class AssistantQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    history: list[AssistantMessage] = Field(default_factory=list, max_length=20)


class RetrievedSource(BaseModel):
    file_path: str
    heading_path: str
    start_line: int
    end_line: int
    distance: float
    # Conteúdo não confiável: a tela renderiza como texto simples (FR-045).
    content: str


class AssistantAnswer(BaseModel):
    status: AssistantStatus
    answer: str | None
    sources: list[RetrievedSource]
    truncated_history: bool
