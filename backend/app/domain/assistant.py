"""Modelos do assistente. `status` é enum fechado — é o que torna FR-043
testável: cada modo de falha tem valor próprio, não string de erro variável.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.domain.models import WorkflowStatus

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


class TicketRefSource(BaseModel):
    """Contexto de chamado citado na pergunta (data-model.md §4). Não é uma
    tabela — derivado a cada pergunta a partir de ``WorkflowDetail``.
    """

    jira_issue_key: str
    status: WorkflowStatus
    subject: str  # conteúdo externo — mesma regra de RetrievedSource.content
    squad_id: str | None


class AssistantAnswer(BaseModel):
    status: AssistantStatus
    answer: str | None
    sources: list[RetrievedSource]
    truncated_history: bool
    ticket_context: TicketRefSource | None = None
