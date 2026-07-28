"""PollingService — pulls Freshservice tickets into the existing ingest path.

Replaces the webhook. Everything downstream is unchanged: the same
``IngestionService``, the same idempotency key, the same outbox.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.freshservice import FreshserviceClientError, FreshserviceClientProtocol
from app.repositories.schema import SyncStateRow
from app.services.ingestion import IngestionService

SOURCE = "freshservice"


class PollingService:
    def __init__(self, session: Session, client: FreshserviceClientProtocol) -> None:
        self._session = session
        self._client = client
        self._ingest = IngestionService(session)

    def poll_once(self) -> dict:
        """Fetch, persist, then advance the watermark. In that order.

        The watermark moves only after the whole page is committed. A failure
        halfway through means the next run re-reads the overlap — which the
        idempotency key answers with ``duplicate``, not a second issue.

        The watermark is the time the poll *started*, never the time it
        finished: a ticket updated during the run would otherwise fall into
        the gap between the two and never be read again.
        """
        started_at = datetime.now(timezone.utc)
        since = self._read_watermark()

        try:
            events = self._client.fetch_updated_since(since)
        except FreshserviceClientError as exc:
            # Watermark untouched — the same window is retried next cycle.
            return {"fetched": 0, "accepted": 0, "duplicates": 0, "error": str(exc)}

        accepted = 0
        duplicates = 0
        for event in events:
            result = self._ingest.ingest(event)
            if result.status == "duplicate":
                duplicates += 1
            else:
                accepted += 1

        self._write_watermark(started_at)
        self._session.commit()
        return {
            "fetched": len(events),
            "accepted": accepted,
            "duplicates": duplicates,
            "error": None,
        }

    # ------------------------------------------------------------------

    def _read_watermark(self) -> datetime | None:
        row = self._session.execute(
            select(SyncStateRow).where(SyncStateRow.source == SOURCE)
        ).scalar_one_or_none()
        return row.last_sync_at if row else None

    def _write_watermark(self, value: datetime) -> None:
        row = self._session.execute(
            select(SyncStateRow).where(SyncStateRow.source == SOURCE)
        ).scalar_one_or_none()
        if row is None:
            self._session.add(SyncStateRow(source=SOURCE, last_sync_at=value))
        else:
            row.last_sync_at = value
