"""Tests for the real JiraClient HTTP adapter."""
from __future__ import annotations

from uuid import UUID

import pytest
import respx
import httpx

from app.domain.models import TicketRecord
from app.integrations.jira import JiraClient, JiraClientError, FakeJiraClient
from app.core.config import Settings


JIRA_URL = "https://example.atlassian.net"
TRACE_ID = UUID("018f0d8a-3d8e-7eef-93b6-2f0b11d31ee0")


@pytest.fixture()
def jira_settings() -> Settings:
    return Settings(
        database_url="postgresql://x:x@localhost/x",  # type: ignore[arg-type]
        jira_base_url=JIRA_URL,  # type: ignore[arg-type]
        jira_email="admin@example.test",
        jira_api_token="secret-token",  # type: ignore[arg-type]
        jira_project_platform="PLAT",
    )


@pytest.fixture()
def jira_client(jira_settings) -> JiraClient:
    return JiraClient(jira_settings)


@pytest.fixture()
def sample_ticket() -> TicketRecord:
    import uuid
    return TicketRecord(
        id=uuid.uuid4(),
        source_ticket_id="FS-100",
        subject="Servico indisponivel",
        description="Aplicacao nao responde.",
        priority="high",
        category="incident",
    )


@respx.mock
def test_jira_client_creates_issue_and_returns_key(jira_client, sample_ticket) -> None:
    respx.post(f"{JIRA_URL}/rest/api/3/issue").respond(201, json={"key": "PLAT-42"})
    key = jira_client.create_issue(sample_ticket, "PLAT", TRACE_ID)
    assert key == "PLAT-42"


@respx.mock
def test_jira_client_sends_freshservice_label_and_trace(jira_client, sample_ticket) -> None:
    route = respx.post(f"{JIRA_URL}/rest/api/3/issue").respond(201, json={"key": "PLAT-1"})
    jira_client.create_issue(sample_ticket, "PLAT", TRACE_ID)

    request_body = route.calls.last.request.read()
    import json
    body = json.loads(request_body)
    labels = body["fields"]["labels"]
    assert f"freshservice-{sample_ticket.source_ticket_id}" in labels
    assert f"trace-{TRACE_ID}" in labels


@respx.mock
def test_jira_client_raises_retryable_on_5xx(jira_client, sample_ticket) -> None:
    respx.post(f"{JIRA_URL}/rest/api/3/issue").respond(503, json={})
    with pytest.raises(JiraClientError) as exc_info:
        jira_client.create_issue(sample_ticket, "PLAT", TRACE_ID)
    assert exc_info.value.retryable is True


@respx.mock
def test_jira_client_raises_terminal_on_4xx(jira_client, sample_ticket) -> None:
    respx.post(f"{JIRA_URL}/rest/api/3/issue").respond(400, json={"errorMessages": ["bad payload"]})
    with pytest.raises(JiraClientError) as exc_info:
        jira_client.create_issue(sample_ticket, "PLAT", TRACE_ID)
    assert exc_info.value.retryable is False


def test_fake_jira_returns_configured_key(sample_ticket) -> None:
    fake = FakeJiraClient(next_key="TEST-999")
    key = fake.create_issue(sample_ticket, "TEST", TRACE_ID)
    assert key == "TEST-999"


def test_fake_jira_raises_error_once_then_succeeds(sample_ticket) -> None:
    fake = FakeJiraClient()
    fake.raise_error(JiraClientError(retryable=True, message="timeout"))
    with pytest.raises(JiraClientError):
        fake.create_issue(sample_ticket, "PLAT", TRACE_ID)
    # Next call succeeds
    key = fake.create_issue(sample_ticket, "PLAT", TRACE_ID)
    assert key == "PLAT-123"
