"""ProcessingService orchestration of the LLM fallback for ambiguous squads.

route_ticket() stays pure and deterministic (see test_processing.py).  These
tests cover the point where ProcessingService consults the LLM only when
``squad_id is None`` — and only when ``LLM_ENABLED`` is true.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.core.config import Settings
from app.domain.models import TicketIngestRequest
from app.integrations.jira import FakeJiraClient
from app.integrations.llm import FakeLLMClient, LLMClientError, SquadClassification
from app.services.ingestion import IngestionService
from app.services.processing import ProcessingService


def _llm_settings(test_database_url: str, **overrides) -> Settings:
    fields = dict(
        database_url=test_database_url,
        jira_project_key="SQD",
        llm_enabled=True,
        llm_model="qwen3:8b",
        llm_confidence_threshold=0.7,
    )
    fields.update(overrides)
    return Settings(**fields)  # type: ignore[arg-type]


def _ingest(session_factory, *, squad: str | None, source_ticket_id: str, event_id: str) -> None:
    session = session_factory()
    try:
        IngestionService(session).ingest(
            TicketIngestRequest(
                event_id=event_id,
                event_type="ticket.created",
                occurred_at=datetime.now(timezone.utc),
                source_ticket_id=source_ticket_id,
                subject="Nao consigo acessar o sistema de RH",
                description="Preciso de ajuda com acesso.",
                category="incident",
                squad=squad,
            )
        )
    finally:
        session.close()


# ---------------------------------------------------------------------------
# 1. Known category never calls the LLM, stays 100% deterministic
# ---------------------------------------------------------------------------


def test_known_squad_never_calls_llm(session_factory, test_database_url, fake_jira: FakeJiraClient) -> None:
    settings = _llm_settings(test_database_url)
    _ingest(session_factory, squad="Squad4", source_ticket_id="FS-LLM-1", event_id="evt-llm-1")

    llm = FakeLLMClient(error=LLMClientError("must not be called"))
    session = session_factory()
    try:
        result = ProcessingService(session, fake_jira, settings, llm_client=llm).process_next()
    finally:
        session.close()

    assert result.status == "completed"
    assert llm.calls == []


# ---------------------------------------------------------------------------
# 2. Unknown category, LLM disabled — unchanged behaviour
# ---------------------------------------------------------------------------


def test_unknown_squad_llm_disabled_keeps_needs_human_review(
    session_factory, test_database_url, fake_jira: FakeJiraClient
) -> None:
    settings = _llm_settings(test_database_url, llm_enabled=False)
    _ingest(session_factory, squad=None, source_ticket_id="FS-LLM-2", event_id="evt-llm-2")

    session = session_factory()
    try:
        result = ProcessingService(session, fake_jira, settings).process_next()
    finally:
        session.close()

    assert result.status == "needs_human_review"


# ---------------------------------------------------------------------------
# 3. Unknown category, LLM enabled, confident valid response above threshold
# ---------------------------------------------------------------------------


def test_unknown_squad_llm_enabled_confident_response_routes(
    session_factory, test_database_url, fake_jira: FakeJiraClient, db_session
) -> None:
    settings = _llm_settings(test_database_url)
    _ingest(session_factory, squad=None, source_ticket_id="FS-LLM-3", event_id="evt-llm-3")

    llm = FakeLLMClient(response=SquadClassification(squad="Squad1", confidence=0.9, reason="acesso"))
    session = session_factory()
    try:
        result = ProcessingService(session, fake_jira, settings, llm_client=llm).process_next()
    finally:
        session.close()

    assert result.status == "completed"
    assert result.jira_issue_key == "SQD-123"

    from sqlalchemy import select
    from app.repositories.schema import RoutingDecisionRow

    decision = db_session.execute(select(RoutingDecisionRow)).scalar_one()
    assert decision.squad_id == "Squad1"
    assert decision.rule_version == "llm/qwen3:8b@squad_classifier_v2"
    assert decision.needs_human_review is False


# ---------------------------------------------------------------------------
# 4. Below-threshold confidence — human review, confidence recorded
# ---------------------------------------------------------------------------


def test_unknown_squad_llm_below_threshold_needs_human_review(
    session_factory, test_database_url, fake_jira: FakeJiraClient, db_session
) -> None:
    settings = _llm_settings(test_database_url)
    _ingest(session_factory, squad=None, source_ticket_id="FS-LLM-4", event_id="evt-llm-4")

    llm = FakeLLMClient(response=SquadClassification(squad="Squad1", confidence=0.4, reason="talvez"))
    session = session_factory()
    try:
        result = ProcessingService(session, fake_jira, settings, llm_client=llm).process_next()
    finally:
        session.close()

    assert result.status == "needs_human_review"

    from sqlalchemy import select
    from app.repositories.schema import RoutingDecisionRow

    decision = db_session.execute(select(RoutingDecisionRow)).scalar_one()
    assert decision.squad_id is None
    assert decision.confidence == 0.4
    assert decision.rule_version == "llm/qwen3:8b@squad_classifier_v2"


def test_unknown_squad_llm_returns_unknown_needs_human_review(
    session_factory, test_database_url, fake_jira: FakeJiraClient
) -> None:
    settings = _llm_settings(test_database_url)
    _ingest(session_factory, squad=None, source_ticket_id="FS-LLM-4b", event_id="evt-llm-4b")

    llm = FakeLLMClient(response=SquadClassification(squad="unknown", confidence=0.95, reason="ambiguo"))
    session = session_factory()
    try:
        result = ProcessingService(session, fake_jira, settings, llm_client=llm).process_next()
    finally:
        session.close()

    assert result.status == "needs_human_review"


# ---------------------------------------------------------------------------
# 5. Degradation — one test per failure mode. Workflow never goes to "failed".
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "error",
    [
        LLMClientError("llm request failed"),  # timeout / connection refused / HTTP error
        LLMClientError("llm returned an invalid response"),  # invalid JSON / missing field / bad enum
    ],
)
def test_llm_failure_degrades_to_human_review_never_fails(
    session_factory, test_database_url, fake_jira: FakeJiraClient, error: LLMClientError
) -> None:
    settings = _llm_settings(test_database_url)
    _ingest(session_factory, squad=None, source_ticket_id=f"FS-LLM-{id(error)}", event_id=f"evt-{id(error)}")

    llm = FakeLLMClient(error=error)
    session = session_factory()
    try:
        result = ProcessingService(session, fake_jira, settings, llm_client=llm).process_next()
    finally:
        session.close()

    assert result.status == "needs_human_review"
    assert result.status != "failed"


# ---------------------------------------------------------------------------
# 6. No ticket content or raw model output leaks into last_error / API
# ---------------------------------------------------------------------------


def test_llm_path_never_leaks_ticket_content_or_raw_output(
    session_factory, test_database_url, fake_jira: FakeJiraClient, db_session
) -> None:
    settings = _llm_settings(test_database_url)
    secret_subject = "SEGREDO-CONFIDENCIAL-xyz"
    session = session_factory()
    try:
        IngestionService(session).ingest(
            TicketIngestRequest(
                event_id="evt-leak-llm",
                event_type="ticket.created",
                occurred_at=datetime.now(timezone.utc),
                source_ticket_id="FS-LLM-LEAK",
                subject=secret_subject,
                description="descricao sigilosa",
                category="incident",
                squad=None,
            )
        )
    finally:
        session.close()

    llm = FakeLLMClient(
        response=SquadClassification(squad="Squad1", confidence=0.4, reason=secret_subject)
    )
    session2 = session_factory()
    try:
        ProcessingService(session2, fake_jira, settings, llm_client=llm).process_next()
    finally:
        session2.close()

    from sqlalchemy import select
    from app.repositories.schema import AuditLogRow, RoutingDecisionRow, WorkflowExecutionRow

    workflow = db_session.execute(select(WorkflowExecutionRow)).scalar_one()
    assert secret_subject not in (workflow.last_error or "")

    decision = db_session.execute(select(RoutingDecisionRow)).scalar_one()
    assert secret_subject not in decision.reason

    for log in db_session.execute(select(AuditLogRow)).scalars():
        assert secret_subject not in log.details_json
