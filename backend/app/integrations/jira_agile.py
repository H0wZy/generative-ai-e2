"""Adaptador de leitura/transição do Jira Agile.

Separado de `jira.py` de propósito: aquele cria issue no fluxo de automação e
já é usado pelo worker. Este só é chamado pelas rotas de Agile, e devolve JSON
cru — quem interpreta é `services/agile.py`.

Erro vira `AgileUnavailable`, que carrega a `reason` nomeada do envelope
(contracts/api-agile.md) em vez de estourar 5xx na cara da tela.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

import httpx

from app.core.config import Settings
from app.domain.agile import AvailabilityReason


@dataclass
class AgileUnavailable(Exception):
    reason: AvailabilityReason
    detail: str

    def __str__(self) -> str:
        return f"AgileUnavailable({self.reason}): {self.detail}"


class JiraAgileClientProtocol(Protocol):
    def get_board_configuration(self, board_id: int) -> dict[str, Any]: ...
    def get_board(self, board_id: int) -> dict[str, Any]: ...
    def get_active_sprint(self, board_id: int) -> dict[str, Any] | None: ...
    def get_closed_sprints(self, board_id: int, limit: int = 5) -> list[dict[str, Any]]: ...
    def get_sprint_issues(
        self, sprint_id: int, with_changelog: bool = False, estimation_field: str | None = None
    ) -> list[dict[str, Any]]: ...
    def get_backlog(
        self, board_id: int, limit: int, offset: int, estimation_field: str | None = None
    ) -> list[dict[str, Any]]: ...
    def get_board_issues(
        self, board_id: int, estimation_field: str | None = None
    ) -> list[dict[str, Any]]: ...
    def get_transitions(self, issue_key: str) -> list[dict[str, Any]]: ...
    def apply_transition(self, issue_key: str, transition_id: str) -> None: ...
    def get_issue_status(self, issue_key: str) -> dict[str, Any]: ...


# Campos pedidos ao Jira. Lista explícita evita trazer descrição e comentário
# — conteúdo de ticket que esta feature não precisa e não deve carregar.
_ISSUE_FIELDS = "summary,status,assignee,labels,priority,parent,issuetype"


def _fields(estimation_field: str | None) -> str:
    """O campo de estimativa é descoberto na configuração do board (R1), então
    entra na lista em tempo de chamada — não é constante."""
    return f"{_ISSUE_FIELDS},{estimation_field}" if estimation_field else _ISSUE_FIELDS

_STATUS_REASON: dict[int, AvailabilityReason] = {
    401: "unauthorized",
    403: "forbidden",
    429: "rate_limited",
}


class JiraAgileClient:
    def __init__(self, settings: Settings) -> None:
        if not settings.jira_is_configured:
            raise RuntimeError("Jira não configurado. Defina JIRA_BASE_URL, JIRA_EMAIL e JIRA_API_TOKEN.")
        self._base_url = str(settings.jira_base_url).rstrip("/")
        self._auth = httpx.BasicAuth(
            username=settings.jira_email or "",
            password=(settings.jira_api_token.get_secret_value() if settings.jira_api_token else ""),
        )
        self._timeout = 30

    # ------------------------------------------------------------------
    # HTTP
    # ------------------------------------------------------------------

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        try:
            with httpx.Client(auth=self._auth, timeout=self._timeout) as client:
                response = client.request(method, f"{self._base_url}{path}", **kwargs)
        except httpx.HTTPError as exc:
            # A mensagem da exceção pode conter a URL, nunca a credencial.
            raise AgileUnavailable("unavailable", f"Falha de rede: {type(exc).__name__}") from exc

        if response.status_code >= 400:
            reason = _STATUS_REASON.get(response.status_code, "unavailable")
            raise AgileUnavailable(reason, f"Jira respondeu HTTP {response.status_code}")
        return response

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return self._request("GET", path, params=params).json()

    # ------------------------------------------------------------------
    # Board
    # ------------------------------------------------------------------

    def get_board_configuration(self, board_id: int) -> dict[str, Any]:
        return self._get(f"/rest/agile/1.0/board/{board_id}/configuration")

    def get_board(self, board_id: int) -> dict[str, Any]:
        return self._get(f"/rest/agile/1.0/board/{board_id}")

    # ------------------------------------------------------------------
    # Sprints
    # ------------------------------------------------------------------

    def get_active_sprint(self, board_id: int) -> dict[str, Any] | None:
        body = self._get(f"/rest/agile/1.0/board/{board_id}/sprint", {"state": "active"})
        values = body.get("values") or []
        return values[0] if values else None

    def get_closed_sprints(self, board_id: int, limit: int = 5) -> list[dict[str, Any]]:
        body = self._get(
            f"/rest/agile/1.0/board/{board_id}/sprint",
            {"state": "closed", "maxResults": limit},
        )
        return list(body.get("values") or [])

    def get_sprint_issues(
        self, sprint_id: int, with_changelog: bool = False, estimation_field: str | None = None
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {"fields": _fields(estimation_field), "maxResults": 100}
        if with_changelog:
            params["expand"] = "changelog"
        body = self._get(f"/rest/agile/1.0/sprint/{sprint_id}/issue", params)
        return list(body.get("issues") or [])

    # ------------------------------------------------------------------
    # Backlog e quadro
    # ------------------------------------------------------------------

    def get_backlog(
        self, board_id: int, limit: int, offset: int, estimation_field: str | None = None
    ) -> list[dict[str, Any]]:
        body = self._get(
            f"/rest/agile/1.0/board/{board_id}/backlog",
            {"fields": _fields(estimation_field), "maxResults": limit, "startAt": offset},
        )
        return list(body.get("issues") or [])

    def get_board_issues(
        self, board_id: int, estimation_field: str | None = None
    ) -> list[dict[str, Any]]:
        body = self._get(
            f"/rest/agile/1.0/board/{board_id}/issue",
            {"fields": _fields(estimation_field), "maxResults": 100},
        )
        return list(body.get("issues") or [])

    # ------------------------------------------------------------------
    # Transição — única escrita desta feature
    # ------------------------------------------------------------------

    def get_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        body = self._get(f"/rest/api/3/issue/{issue_key}/transitions")
        return list(body.get("transitions") or [])

    def apply_transition(self, issue_key: str, transition_id: str) -> None:
        self._request(
            "POST",
            f"/rest/api/3/issue/{issue_key}/transitions",
            json={"transition": {"id": transition_id}},
        )

    def get_issue_status(self, issue_key: str) -> dict[str, Any]:
        body = self._get(f"/rest/api/3/issue/{issue_key}", {"fields": "status"})
        return body.get("fields", {}).get("status") or {}


# ---------------------------------------------------------------------------
# Fake — suíte roda sem credencial e sem rede (Princípio IV)
# ---------------------------------------------------------------------------

_FAKE_STATUSES = {
    "10004": "A fazer",
    "10005": "Fazendo",
    "10006": "Em análise",
    "10007": "Feito",
}


def _fake_issue(
    key: str,
    status_id: str,
    points: float | None,
    assignee: str | None = None,
    parent: tuple[str, str] | None = None,
    labels: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "key": key,
        "fields": {
            "summary": f"Item {key}",
            "status": {"id": status_id, "name": _FAKE_STATUSES[status_id]},
            "assignee": {"displayName": assignee} if assignee else None,
            "labels": labels or [],
            "priority": {"name": "Medium"},
            "parent": (
                {"key": parent[0], "fields": {"summary": parent[1]}} if parent else None
            ),
            "customfield_10016": points,
        },
    }


@dataclass
class FakeJiraAgileClient:
    """Fixture determinística que reproduz o board FRESH medido.

    Inclui a auto-transição (`Em análise` -> `Em análise`) que o Jira real
    devolve — é ela que torna a guarda de `already_there` necessária no
    servidor (research.md R12b).
    """

    error: AgileUnavailable | None = None
    applied: list[tuple[str, str]] = field(default_factory=list)
    _status_by_issue: dict[str, str] = field(
        default_factory=lambda: {"FRESH-1": "10004", "FRESH-2": "10006", "FRESH-3": "10005"}
    )

    def _check(self) -> None:
        if self.error is not None:
            raise self.error

    def get_board_configuration(self, board_id: int) -> dict[str, Any]:
        self._check()
        return {
            "id": board_id,
            "name": "FRESH board",
            "columnConfig": {
                "columns": [
                    {"name": "A fazer", "statuses": [{"id": "10004"}]},
                    {"name": "Fazendo", "statuses": [{"id": "10005"}], "min": 1, "max": 2},
                    {"name": "Em análise", "statuses": [{"id": "10006"}]},
                    {"name": "Feito", "statuses": [{"id": "10007"}]},
                ],
                "constraintType": "issueCount",
            },
            "estimation": {
                "type": "field",
                "field": {"fieldId": "customfield_10016", "displayName": "Story point estimate"},
            },
            "ranking": {"rankCustomFieldId": 10019},
        }

    def get_board(self, board_id: int) -> dict[str, Any]:
        self._check()
        return {"id": board_id, "name": "FRESH board", "type": "simple"}

    def get_active_sprint(self, board_id: int) -> dict[str, Any] | None:
        self._check()
        return {
            "id": 2,
            "name": "FRESH Sprint 1",
            "state": "active",
            "goal": "",  # o Jira devolve string vazia, não null
            "startDate": "2026-07-27T09:00:00.000Z",
            "endDate": "2026-08-10T18:00:00.000Z",
        }

    def get_closed_sprints(self, board_id: int, limit: int = 5) -> list[dict[str, Any]]:
        self._check()
        return []

    def get_sprint_issues(
        self, sprint_id: int, with_changelog: bool = False, estimation_field: str | None = None
    ) -> list[dict[str, Any]]:
        self._check()
        issues = [
            _fake_issue("FRESH-1", "10004", 3.0, "Ana Lima", ("FRESH-100", "Épico de integração")),
            _fake_issue("FRESH-2", "10006", 5.0, "Bruno Sá", ("FRESH-100", "Épico de integração")),
            _fake_issue("FRESH-3", "10005", 2.0, None, None, ["blocked"]),
        ]
        if with_changelog:
            issues[0]["changelog"] = {"histories": []}
            issues[1]["changelog"] = {
                "histories": [
                    {
                        "created": "2026-07-28T10:00:00.000Z",
                        "items": [{"field": "status", "to": "10006", "toString": "Em análise"}],
                    }
                ]
            }
            issues[2]["changelog"] = {"histories": []}
        return issues

    def get_backlog(
        self, board_id: int, limit: int, offset: int, estimation_field: str | None = None
    ) -> list[dict[str, Any]]:
        self._check()
        items = [
            _fake_issue(f"FRESH-{n}", "10004", float(n % 5), None, ("FRESH-100", "Épico de integração"))
            for n in range(10, 20)
        ]
        return items[offset : offset + limit]

    def get_board_issues(
        self, board_id: int, estimation_field: str | None = None
    ) -> list[dict[str, Any]]:
        self._check()
        return [
            _fake_issue(key, status_id, 1.0)
            for key, status_id in self._status_by_issue.items()
        ]

    def get_transitions(self, issue_key: str) -> list[dict[str, Any]]:
        self._check()
        # Como o board real: toda coluna é alcançável, inclusive a atual.
        return [
            {"id": "11", "name": "A fazer", "to": {"id": "10004", "name": "A fazer"}},
            {"id": "21", "name": "Fazendo", "to": {"id": "10005", "name": "Fazendo"}},
            {"id": "31", "name": "Em análise", "to": {"id": "10006", "name": "Em análise"}},
            {"id": "41", "name": "Feito", "to": {"id": "10007", "name": "Feito"}},
        ]

    def apply_transition(self, issue_key: str, transition_id: str) -> None:
        self._check()
        target = {"11": "10004", "21": "10005", "31": "10006", "41": "10007"}[transition_id]
        self._status_by_issue[issue_key] = target
        self.applied.append((issue_key, transition_id))

    def get_issue_status(self, issue_key: str) -> dict[str, Any]:
        self._check()
        status_id = self._status_by_issue.get(issue_key, "10004")
        return {"id": status_id, "name": _FAKE_STATUSES[status_id]}
