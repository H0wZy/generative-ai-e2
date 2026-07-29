"""Tests for JiraAgileClient — HTTP mocked with respx, no network, no token."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.core.config import Settings
from app.integrations.jira_agile import AgileUnavailable, JiraAgileClient

BASE = "https://example.atlassian.net"


@pytest.fixture()
def client() -> JiraAgileClient:
    settings = Settings(
        database_url="postgresql://u:p@localhost:5432/db",  # type: ignore[arg-type]
        jira_base_url=BASE,  # type: ignore[arg-type]
        jira_email="user@example.test",
        jira_api_token="token-de-teste",  # type: ignore[arg-type]
        jira_project_key="FRESH",
        jira_board_id=2,
    )
    return JiraAgileClient(settings)


@respx.mock
def test_board_configuration_with_wip_max(client: JiraAgileClient) -> None:
    respx.get(f"{BASE}/rest/agile/1.0/board/2/configuration").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "FRESH board",
                "columnConfig": {
                    "columns": [{"name": "Fazendo", "statuses": [{"id": "3"}], "min": 2, "max": 4}],
                    "constraintType": "issueCount",
                },
                "estimation": {"type": "field", "field": {"fieldId": "customfield_10016"}},
            },
        )
    )
    raw = client.get_board_configuration(2)
    column = raw["columnConfig"]["columns"][0]
    assert column["max"] == 4
    assert raw["estimation"]["field"]["fieldId"] == "customfield_10016"


@respx.mock
def test_board_configuration_without_max(client: JiraAgileClient) -> None:
    respx.get(f"{BASE}/rest/agile/1.0/board/2/configuration").mock(
        return_value=httpx.Response(
            200,
            json={
                "name": "FRESH board",
                "columnConfig": {
                    "columns": [{"name": "A fazer", "statuses": [{"id": "10004"}]}],
                    "constraintType": "none",
                },
                "estimation": {"type": "none"},
            },
        )
    )
    raw = client.get_board_configuration(2)
    assert "max" not in raw["columnConfig"]["columns"][0]
    assert raw["estimation"]["type"] == "none"


@respx.mock
def test_active_sprint_absent_returns_none(client: JiraAgileClient) -> None:
    respx.get(f"{BASE}/rest/agile/1.0/board/2/sprint").mock(
        return_value=httpx.Response(200, json={"values": []})
    )
    assert client.get_active_sprint(2) is None


@respx.mock
def test_active_sprint_present(client: JiraAgileClient) -> None:
    respx.get(f"{BASE}/rest/agile/1.0/board/2/sprint").mock(
        return_value=httpx.Response(200, json={"values": [{"id": 2, "name": "FRESH Sprint 1"}]})
    )
    sprint = client.get_active_sprint(2)
    assert sprint is not None and sprint["id"] == 2


@respx.mock
@pytest.mark.parametrize(
    ("status_code", "reason"),
    [(401, "unauthorized"), (403, "forbidden"), (429, "rate_limited"), (500, "unavailable")],
)
def test_http_errors_map_to_named_reasons(client: JiraAgileClient, status_code, reason) -> None:
    respx.get(f"{BASE}/rest/agile/1.0/board/2/configuration").mock(
        return_value=httpx.Response(status_code, json={"errorMessages": ["nope"]})
    )
    with pytest.raises(AgileUnavailable) as exc:
        client.get_board_configuration(2)
    assert exc.value.reason == reason


@respx.mock
def test_network_failure_is_unavailable_and_leaks_no_credential(client: JiraAgileClient) -> None:
    respx.get(f"{BASE}/rest/agile/1.0/board/2/configuration").mock(
        side_effect=httpx.ConnectError("boom")
    )
    with pytest.raises(AgileUnavailable) as exc:
        client.get_board_configuration(2)
    assert exc.value.reason == "unavailable"
    assert "token-de-teste" not in str(exc.value)


@respx.mock
def test_apply_transition_posts_transition_id(client: JiraAgileClient) -> None:
    route = respx.post(f"{BASE}/rest/api/3/issue/FRESH-2/transitions").mock(
        return_value=httpx.Response(204)
    )
    client.apply_transition("FRESH-2", "31")
    assert route.called
    assert route.calls[0].request.read() == b'{"transition":{"id":"31"}}'


@respx.mock
def test_sprint_issues_requests_changelog_only_when_asked(client: JiraAgileClient) -> None:
    route = respx.get(f"{BASE}/rest/agile/1.0/sprint/2/issue").mock(
        return_value=httpx.Response(200, json={"issues": []})
    )
    client.get_sprint_issues(2)
    assert "expand" not in route.calls[0].request.url.params

    client.get_sprint_issues(2, with_changelog=True)
    assert route.calls[1].request.url.params["expand"] == "changelog"
