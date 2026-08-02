"""Jira REST API adapter.

The real adapter (``JiraClient``) sends HTTP requests via HTTPX.
The fake (``FakeJiraClient``) is used in tests — no network calls.
Both share the ``JiraClientProtocol`` interface.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

import httpx

from app.core.config import Settings
from app.domain.models import TicketRecord


# ---------------------------------------------------------------------------
# Error types
# ---------------------------------------------------------------------------


@dataclass
class JiraClientError(Exception):
    retryable: bool
    message: str

    def __str__(self) -> str:
        kind = "retryable" if self.retryable else "terminal"
        return f"JiraClientError({kind}): {self.message}"


# ---------------------------------------------------------------------------
# Protocol / interface
# ---------------------------------------------------------------------------


class JiraClientProtocol(Protocol):
    def create_issue(
        self,
        ticket: TicketRecord,
        project_key: str,
        internal_correlation_id: UUID,
        squad_id: str,
    ) -> str:
        """Return the Jira issue key (e.g. 'SQD-123')."""
        ...


# ---------------------------------------------------------------------------
# Real adapter
# ---------------------------------------------------------------------------


def to_atlassian_document(text: str) -> dict:
    """Convert plain text to Atlassian Document Format (ADF)."""
    return {
        "type": "doc",
        "version": 1,
        "content": [
            {
                "type": "paragraph",
                "content": [{"type": "text", "text": text or "-"}],
            }
        ],
    }


PRIORITY_MAP = {
    "urgent": "Highest",
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}

# HTTP status codes that should trigger a retry
_RETRYABLE_STATUS = {408, 429, 500, 502, 503, 504}


class JiraClient:
    """Real Jira REST API v3 adapter.

    Requires ``settings.jira_base_url``, ``settings.jira_email`` and
    ``settings.jira_api_token`` to be set at construction time.
    """

    def __init__(self, settings: Settings) -> None:
        if not settings.jira_is_configured:
            raise RuntimeError(
                "Jira is not configured. "
                "Set JIRA_BASE_URL, JIRA_EMAIL and JIRA_API_TOKEN."
            )
        self._base_url = str(settings.jira_base_url).rstrip("/")
        self._auth = httpx.BasicAuth(
            username=settings.jira_email or "",
            password=(settings.jira_api_token.get_secret_value() if settings.jira_api_token else ""),
        )

    def create_issue(
        self,
        ticket: TicketRecord,
        project_key: str,
        internal_correlation_id: UUID,
        squad_id: str,
    ) -> str:
        payload = {
            "fields": {
                "project": {"key": project_key},
                "summary": ticket.subject,
                "description": to_atlassian_document(ticket.description),
                "issuetype": {"name": "Tarefa"},  # sandbox project has no "Task" type, only pt-BR names
                # freshservice-<id> is the structured link: the ticket number no
                # longer depends on someone typing it into the summary.
                "labels": [
                    f"freshservice-{ticket.source_ticket_id}",
                    f"trace-{internal_correlation_id}",
                    f"squad-{squad_id}",
                ],
            }
        }

        try:
            with httpx.Client(auth=self._auth, timeout=30) as client:
                response = client.post(
                    f"{self._base_url}/rest/api/3/issue",
                    json=payload,
                )
        except httpx.HTTPError as exc:
            raise JiraClientError(retryable=True, message=f"Falha de rede: {type(exc).__name__}") from exc

        self._raise_for_status(response)
        return response.json()["key"]

    @staticmethod
    def _raise_for_status(response: httpx.Response) -> None:
        if response.status_code == 201:
            return
        retryable = response.status_code in _RETRYABLE_STATUS
        raise JiraClientError(
            retryable=retryable,
            message=f"HTTP {response.status_code}",
        )


# ---------------------------------------------------------------------------
# Fake adapter for tests
# ---------------------------------------------------------------------------


@dataclass
class FakeJiraClient:
    """Deterministic fake — derives issue keys from project_key, or raises errors.

    The counter matters: every squad now lands in the same project, so a fake
    that always returned ``<PROJECT>-123`` would hand out a duplicate key —
    something real Jira never does, and which the unique constraint on
    ``jira_issue_links.jira_issue_key`` rightly rejects.
    """

    _error: JiraClientError | None = field(default=None, init=False, repr=False)
    _next_number: int = field(default=123, init=False, repr=False)
    last_labels: list[str] = field(default_factory=list, init=False)

    def raise_error(self, error: JiraClientError) -> None:
        self._error = error

    def create_issue(
        self,
        ticket: TicketRecord,
        project_key: str,
        internal_correlation_id: UUID,
        squad_id: str,
    ) -> str:
        if self._error is not None:
            err = self._error
            self._error = None
            raise err
        self.last_labels = [
            f"freshservice-{ticket.source_ticket_id}",
            f"trace-{internal_correlation_id}",
            f"squad-{squad_id}",
        ]
        key = f"{project_key}-{self._next_number}"
        self._next_number += 1
        return key
