"""Freshservice read adapter — polling, not webhook.

Freshservice is a cloud tenant. For it to deliver a webhook, this API would
have to be publicly reachable, which would mean a tunnel plus boundary
authentication the MVP does not have. Polling keeps the surface local, removes
the webhook signing secret, and reuses the ``updated_since`` watermark pattern.

``FreshserviceClient`` talks HTTP; ``FakeFreshserviceClient`` is the test
double. Both share ``FreshserviceClientProtocol``.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

import httpx

from app.core.config import Settings
from app.domain.models import TicketIngestRequest
from app.integrations.errors import (
    ErrorCategory,
    categorize_exception,
    categorize_status,
    format_error,
    is_retryable,
)

PAGE_SIZE = 100

# Freshservice priority is an integer 1..4. Anything else falls back to medium.
_PRIORITY_BY_CODE = {1: "low", 2: "medium", 3: "high", 4: "urgent"}

# The squad may be a native field or a custom field, depending on the tenant.
# Both are tried, in this order. Confirmed against the sandbox before F2 closes.
_SQUAD_FIELDS = ("squad", "group_name")
_SQUAD_CUSTOM_FIELDS = ("squad", "time", "equipe")


@dataclass
class FreshserviceClientError(Exception):
    """Failure while reading from Freshservice.

    ``category`` separates a rejected credential from a blocked network — a
    corporate proxy answering 403 looks exactly like a bad API key, and
    debugging the wrong one costs hours. The message never contains the key
    or the response body.
    """

    category: ErrorCategory
    detail: str

    @property
    def retryable(self) -> bool:
        return is_retryable(self.category)

    def __str__(self) -> str:
        return format_error(self.category, self.detail)


class FreshserviceClientProtocol(Protocol):
    def fetch_updated_since(self, since: datetime | None) -> list[TicketIngestRequest]:
        """Return ticket events updated after ``since`` (all pages)."""
        ...


def _priority(raw: Any) -> str:
    try:
        return _PRIORITY_BY_CODE.get(int(raw), "medium")
    except (TypeError, ValueError):
        return "medium"


def _squad(ticket: dict) -> str | None:
    """Pull the squad out of a ticket, native field or custom field.

    Returns the raw string. Validating it against the closed enum is routing's
    job, not the adapter's — the adapter must not silently drop a value the
    routing layer would want to log as unknown.
    """
    for name in _SQUAD_FIELDS:
        value = ticket.get(name)
        if value:
            return str(value)[:40]
    custom = ticket.get("custom_fields") or {}
    for name in _SQUAD_CUSTOM_FIELDS:
        value = custom.get(name)
        if value:
            return str(value)[:40]
    return None


def to_ingest_request(ticket: dict) -> TicketIngestRequest:
    """Map one Freshservice ticket to the internal ingest contract.

    ``event_id`` carries ``updated_at`` so an edit produces a new event while
    re-reading an unchanged ticket produces the same idempotency key — which
    the ingest layer answers with ``duplicate``.
    """
    source_ticket_id = str(ticket.get("id", ""))
    updated_at = str(ticket.get("updated_at", ""))
    return TicketIngestRequest(
        event_id=f"fs-{source_ticket_id}-{updated_at}"[:128],
        event_type="ticket.created",
        occurred_at=ticket.get("created_at") or ticket.get("updated_at"),
        source_ticket_id=source_ticket_id[:80],
        subject=(ticket.get("subject") or "(sem assunto)")[:255],
        description=(ticket.get("description_text") or ticket.get("description") or "")[:20_000],
        priority=_priority(ticket.get("priority")),
        category=(ticket.get("category") or None),
        squad=_squad(ticket),
        requester=None,  # requester is PII and nothing downstream needs it
        attachments=[],
        external_correlation_id=f"fs-poll-{source_ticket_id}"[:128],
    )


class FreshserviceClient:
    """Real adapter — Freshservice API v2, Basic Auth with the API key."""

    def __init__(self, settings: Settings) -> None:
        if not settings.freshservice_is_configured:
            raise RuntimeError(
                "Freshservice is not configured. "
                "Set FRESHSERVICE_DOMAIN and FRESHSERVICE_API_KEY."
            )
        domain = (settings.freshservice_domain or "").rstrip("/")
        self._base_url = domain if domain.startswith("http") else f"https://{domain}"
        key = settings.freshservice_api_key
        # Freshservice takes the API key as the username and ignores the password.
        self._auth = httpx.BasicAuth(
            username=key.get_secret_value() if key else "",
            password="X",
        )

    def fetch_updated_since(self, since: datetime | None) -> list[TicketIngestRequest]:
        params: dict[str, Any] = {"per_page": PAGE_SIZE}
        if since is not None:
            params["updated_since"] = since.isoformat()

        collected: list[TicketIngestRequest] = []
        page = 1
        while True:
            payload = self._get_page({**params, "page": page})
            tickets = payload.get("tickets", [])
            collected.extend(to_ingest_request(t) for t in tickets)
            if len(tickets) < PAGE_SIZE:
                break
            page += 1
        return collected

    def _get_page(self, params: dict) -> dict:
        try:
            with httpx.Client(auth=self._auth, timeout=30) as client:
                response = client.get(f"{self._base_url}/api/v2/tickets", params=params)
        except httpx.HTTPError as exc:
            raise FreshserviceClientError(
                category=categorize_exception(exc),
                detail=type(exc).__name__,
            ) from None

        if response.status_code != 200:
            raise FreshserviceClientError(
                category=categorize_status(response.status_code),
                detail=f"HTTP {response.status_code}",
            )
        try:
            return response.json()
        except ValueError:
            raise FreshserviceClientError(category="business", detail="invalid JSON") from None


@dataclass
class FakeFreshserviceClient:
    """Deterministic double — returns configured tickets or raises."""

    tickets: list[dict] = field(default_factory=list)
    error: FreshserviceClientError | None = None
    calls: list[datetime | None] = field(default_factory=list)

    def fetch_updated_since(self, since: datetime | None) -> list[TicketIngestRequest]:
        self.calls.append(since)
        if self.error is not None:
            raise self.error
        return [to_ingest_request(t) for t in self.tickets]
