"""IngestionService — validates and persists one ticket event."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.domain.models import IngestResponse, TicketIngestRequest
from app.repositories.workflows import WorkflowRepository


class IngestionService:
    def __init__(self, session: Session) -> None:
        self._repo = WorkflowRepository(session)

    def ingest(self, payload: TicketIngestRequest) -> IngestResponse:
        return self._repo.ingest(payload)
