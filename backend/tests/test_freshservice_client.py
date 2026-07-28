"""Freshservice polling adapter and PollingService — no network, respx only."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx
import pytest
import respx
from sqlalchemy import select

from app.core.config import Settings
from app.integrations.freshservice import (
    PAGE_SIZE,
    FakeFreshserviceClient,
    FreshserviceClient,
    FreshserviceClientError,
    to_ingest_request,
)
from app.repositories.schema import SyncStateRow, TicketRow
from app.services.polling import PollingService

FS_DOMAIN = "acme.freshservice.com"
FS_URL = f"https://{FS_DOMAIN}/api/v2/tickets"


@pytest.fixture()
def fs_settings(test_database_url: str) -> Settings:
    return Settings(
        database_url=test_database_url,  # type: ignore[arg-type]
        freshservice_domain=FS_DOMAIN,
        freshservice_api_key="fs-secret-key",  # type: ignore[arg-type]
    )


def _ticket(ticket_id: int = 143695, updated_at: str = "2026-07-27T10:00:00Z", **overrides) -> dict:
    base = {
        "id": ticket_id,
        "subject": "Job de carga falhou",
        "description_text": "A carga abortou as 02h.",
        "priority": 3,
        "category": "incident",
        "squad": "SQUAD-01",
        "created_at": "2026-07-27T09:00:00Z",
        "updated_at": updated_at,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Mapping
# ---------------------------------------------------------------------------


def test_maps_ticket_fields_including_squad() -> None:
    event = to_ingest_request(_ticket())
    assert event.source_ticket_id == "143695"
    assert event.squad == "SQUAD-01"
    assert event.priority == "high"
    assert event.category == "incident"


def test_squad_missing_is_none_not_dropped_silently() -> None:
    event = to_ingest_request(_ticket(squad=None))
    assert event.squad is None


def test_squad_outside_enum_is_passed_through_not_dropped() -> None:
    """The adapter does not validate the enum — routing does.

    Silently dropping an unknown value would hide the very case the LLM
    fallback exists for.
    """
    event = to_ingest_request(_ticket(squad="SquadInexistente"))
    assert event.squad == "SquadInexistente"


def test_requester_is_never_carried_over() -> None:
    event = to_ingest_request(_ticket(requester_id=42, email="pessoa@acme.com"))
    assert event.requester is None


def test_event_id_changes_with_updated_at() -> None:
    """An edit is a new event; an unchanged re-read is the same event."""
    first = to_ingest_request(_ticket(updated_at="2026-07-27T10:00:00Z"))
    same = to_ingest_request(_ticket(updated_at="2026-07-27T10:00:00Z"))
    edited = to_ingest_request(_ticket(updated_at="2026-07-27T11:00:00Z"))
    assert first.event_id == same.event_id
    assert first.event_id != edited.event_id


# ---------------------------------------------------------------------------
# HTTP behaviour
# ---------------------------------------------------------------------------


@respx.mock
def test_fetch_returns_tickets_and_sends_updated_since(fs_settings) -> None:
    route = respx.get(FS_URL).respond(200, json={"tickets": [_ticket()]})
    since = datetime(2026, 7, 27, 8, 0, tzinfo=timezone.utc)

    events = FreshserviceClient(fs_settings).fetch_updated_since(since)

    assert len(events) == 1
    assert "updated_since" in route.calls.last.request.url.params


@respx.mock
def test_fetch_with_no_watermark_omits_updated_since(fs_settings) -> None:
    route = respx.get(FS_URL).respond(200, json={"tickets": []})
    FreshserviceClient(fs_settings).fetch_updated_since(None)
    assert "updated_since" not in route.calls.last.request.url.params


@respx.mock
def test_fetch_follows_pagination(fs_settings) -> None:
    full_page = [_ticket(ticket_id=i, updated_at="2026-07-27T10:00:00Z") for i in range(PAGE_SIZE)]
    respx.get(FS_URL).mock(
        side_effect=[
            httpx.Response(200, json={"tickets": full_page}),
            httpx.Response(200, json={"tickets": [_ticket(ticket_id=999)]}),
        ]
    )
    events = FreshserviceClient(fs_settings).fetch_updated_since(None)
    assert len(events) == PAGE_SIZE + 1


@respx.mock
def test_empty_page_returns_nothing(fs_settings) -> None:
    respx.get(FS_URL).respond(200, json={"tickets": []})
    assert FreshserviceClient(fs_settings).fetch_updated_since(None) == []


@pytest.mark.parametrize(
    ("status", "expected_category", "retryable"),
    [
        (401, "auth", False),
        (403, "auth", False),
        (429, "connectivity", True),
        (503, "connectivity", True),
        (422, "business", False),
    ],
)
@respx.mock
def test_http_status_maps_to_category(fs_settings, status, expected_category, retryable) -> None:
    """A blocked proxy answering 403 must not read like a bad key.

    That is exactly the confusion this categorization exists to prevent.
    """
    respx.get(FS_URL).respond(status, json={"message": "nope", "token": "leak-me-abc123"})

    with pytest.raises(FreshserviceClientError) as exc_info:
        FreshserviceClient(fs_settings).fetch_updated_since(None)

    assert exc_info.value.category == expected_category
    assert exc_info.value.retryable is retryable
    assert "leak-me-abc123" not in str(exc_info.value)


@respx.mock
def test_timeout_is_connectivity_not_auth(fs_settings) -> None:
    respx.get(FS_URL).mock(side_effect=httpx.ConnectTimeout("timed out"))
    with pytest.raises(FreshserviceClientError) as exc_info:
        FreshserviceClient(fs_settings).fetch_updated_since(None)
    assert exc_info.value.category == "connectivity"


@respx.mock
def test_error_never_contains_the_api_key(fs_settings) -> None:
    respx.get(FS_URL).respond(401, json={})
    with pytest.raises(FreshserviceClientError) as exc_info:
        FreshserviceClient(fs_settings).fetch_updated_since(None)
    assert "fs-secret-key" not in str(exc_info.value)


def test_client_refuses_to_build_without_credentials(test_database_url: str) -> None:
    settings = Settings(database_url=test_database_url)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError):
        FreshserviceClient(settings)


# ---------------------------------------------------------------------------
# PollingService — watermark and idempotency
# ---------------------------------------------------------------------------


def test_poll_ingests_tickets_and_sets_watermark(session_factory, db_session) -> None:
    client = FakeFreshserviceClient(tickets=[_ticket(), _ticket(ticket_id=143696)])

    session = session_factory()
    try:
        summary = PollingService(session, client).poll_once()
    finally:
        session.close()

    assert summary["fetched"] == 2
    assert summary["accepted"] == 2
    assert db_session.execute(select(SyncStateRow)).scalar_one().last_sync_at is not None
    assert len(db_session.execute(select(TicketRow)).scalars().all()) == 2


def test_second_poll_of_unchanged_tickets_is_all_duplicates(session_factory, db_session) -> None:
    client = FakeFreshserviceClient(tickets=[_ticket()])

    for _ in range(2):
        session = session_factory()
        try:
            summary = PollingService(session, client).poll_once()
        finally:
            session.close()

    assert summary["accepted"] == 0
    assert summary["duplicates"] == 1
    assert len(db_session.execute(select(TicketRow)).scalars().all()) == 1


def test_second_poll_passes_the_stored_watermark(session_factory) -> None:
    client = FakeFreshserviceClient(tickets=[])

    for _ in range(2):
        session = session_factory()
        try:
            PollingService(session, client).poll_once()
        finally:
            session.close()

    assert client.calls[0] is None
    assert client.calls[1] is not None


def test_watermark_is_poll_start_not_poll_end(session_factory, db_session) -> None:
    """A ticket updated mid-poll must not fall into a gap.

    Storing the finish time would skip anything that changed while the page
    was being read.
    """
    before = datetime.now(timezone.utc)
    client = FakeFreshserviceClient(tickets=[_ticket()])

    session = session_factory()
    try:
        PollingService(session, client).poll_once()
    finally:
        session.close()

    stored = db_session.execute(select(SyncStateRow)).scalar_one().last_sync_at
    assert stored >= before - timedelta(seconds=1)
    assert stored <= datetime.now(timezone.utc)


def test_fetch_failure_leaves_the_watermark_untouched(session_factory, db_session) -> None:
    """Failure must retry the same window, not skip it."""
    ok_client = FakeFreshserviceClient(tickets=[_ticket()])
    session = session_factory()
    try:
        PollingService(session, ok_client).poll_once()
    finally:
        session.close()
    first_watermark = db_session.execute(select(SyncStateRow)).scalar_one().last_sync_at

    failing = FakeFreshserviceClient(
        error=FreshserviceClientError(category="connectivity", detail="HTTP 503")
    )
    session2 = session_factory()
    try:
        summary = PollingService(session2, failing).poll_once()
    finally:
        session2.close()

    assert summary["error"] == "connectivity:HTTP 503"
    db_session.expire_all()
    assert db_session.execute(select(SyncStateRow)).scalar_one().last_sync_at == first_watermark
