"""Rotas de Agile — leitura do Jira pelo backend.

Nenhuma credencial chega ao navegador (FR-031). Indisponibilidade responde
**200** com envelope nomeado, não 5xx: um erro derrubaria o `error.tsx` da
rota e levaria a seção inteira junto (contracts/api-agile.md).
"""
from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse

from app.core.config import Settings
from app.domain.agile import BoardConfig, Envelope, TransitionRequest, TransitionResult
from app.integrations.jira_agile import (
    AgileUnavailable,
    FakeJiraAgileClient,
    JiraAgileClient,
    JiraAgileClientProtocol,
)
from app.services import agile as service
from app.services.cache import TTLCache

_NOT_CONFIGURED = Envelope[Any](
    available=False,
    reason="not_configured",
    detail="JIRA_BOARD_ID não configurado",
    data=None,
)


def create_agile_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/api/v1/agile", tags=["agile"])
    cache = TTLCache(ttl_seconds=60)

    def get_client() -> JiraAgileClientProtocol:
        if settings.agile_is_configured:
            return JiraAgileClient(settings)
        return FakeJiraAgileClient()

    router.get_client = get_client  # type: ignore[attr-defined]

    def _board_id() -> int:
        return settings.jira_board_id or 0

    def _config(client: JiraAgileClientProtocol) -> BoardConfig:
        board_id = _board_id()
        raw = client.get_board_configuration(board_id)
        return service.parse_board_config(board_id, raw)

    # ------------------------------------------------------------------

    @router.get("/sprint", response_model=Envelope[Any])
    def get_sprint(client: JiraAgileClientProtocol = Depends(get_client)) -> Envelope[Any]:
        if not settings.agile_is_configured:
            return _NOT_CONFIGURED

        key = ("sprint", _board_id())
        cached = cache.get(key)
        if cached is not None:
            return cached

        try:
            config = _config(client)
            sprint_raw = client.get_active_sprint(_board_id())

            if sprint_raw is None:
                data: dict[str, Any] = {
                    "board": {"board_id": config.board_id, "name": config.name},
                    "sprint": None,
                    "burndown": None,
                    "velocity": [],
                    "blocked": None,
                }
            else:
                issues_raw = client.get_sprint_issues(
                    sprint_raw["id"], with_changelog=True, estimation_field=config.estimation_field_id
                )
                items = service.parse_issues(issues_raw, config)
                closed = [
                    (raw, service.parse_issues(
                        client.get_sprint_issues(
                            raw["id"], estimation_field=config.estimation_field_id
                        ),
                        config,
                    ))
                    for raw in client.get_closed_sprints(_board_id())
                ]
                data = {
                    "board": {"board_id": config.board_id, "name": config.name},
                    "sprint": service.build_sprint(
                        sprint_raw, items, config, issues_raw=issues_raw
                    ).model_dump(),
                    "burndown": (
                        b.model_dump()
                        if (b := service.build_burndown(sprint_raw, issues_raw, config))
                        else None
                    ),
                    "velocity": [v.model_dump() for v in service.build_velocity(closed, config)],
                    "blocked": [
                        item.model_dump() for item in items if item.blocked_reason is not None
                    ],
                }
        except AgileUnavailable as exc:
            return Envelope[Any](available=False, reason=exc.reason, detail=exc.detail, data=None)

        envelope = Envelope[Any](available=True, data=data)
        cache.set(key, envelope)
        return envelope

    @router.get("/backlog", response_model=Envelope[Any])
    def get_backlog(
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        client: JiraAgileClientProtocol = Depends(get_client),
    ) -> Envelope[Any]:
        if not settings.agile_is_configured:
            return _NOT_CONFIGURED

        key = ("backlog", _board_id(), limit, offset)
        cached = cache.get(key)
        if cached is not None:
            return cached

        try:
            config = _config(client)
            raws = client.get_backlog(
                _board_id(), limit, offset, estimation_field=config.estimation_field_id
            )
            view = service.build_backlog(service.parse_issues(raws, config), config)
        except AgileUnavailable as exc:
            return Envelope[Any](available=False, reason=exc.reason, detail=exc.detail, data=None)

        envelope = Envelope[Any](available=True, data=view.model_dump())
        cache.set(key, envelope)
        return envelope

    @router.get("/board", response_model=Envelope[Any])
    def get_board(
        scope: Literal["sprint", "board"] = Query(default="sprint"),
        client: JiraAgileClientProtocol = Depends(get_client),
    ) -> Envelope[Any]:
        if not settings.agile_is_configured:
            return _NOT_CONFIGURED

        key = ("board", _board_id(), scope)
        cached = cache.get(key)
        if cached is not None:
            return cached

        try:
            config = _config(client)
            if scope == "sprint":
                sprint_raw = client.get_active_sprint(_board_id())
                if sprint_raw is None:
                    # Sem sprint ativo o Scrum não tem quadro — e isso é
                    # disponibilidade normal, não erro.
                    envelope = Envelope[Any](
                        available=True, data={"columns": [], "constraint_type": "none"}
                    )
                    cache.set(key, envelope)
                    return envelope
                raws = client.get_sprint_issues(
                    sprint_raw["id"], estimation_field=config.estimation_field_id
                )
            else:
                raws = client.get_board_issues(
                    _board_id(), estimation_field=config.estimation_field_id
                )

            items = service.parse_issues(raws, config)
            data = {
                "constraint_type": config.constraint_type,
                "columns": service.build_board_columns(config, items),
            }
        except AgileUnavailable as exc:
            return Envelope[Any](available=False, reason=exc.reason, detail=exc.detail, data=None)

        envelope = Envelope[Any](available=True, data=data)
        cache.set(key, envelope)
        return envelope

    @router.post("/issues/{issue_key}/transition", response_model=TransitionResult)
    def transition(
        issue_key: str,
        payload: TransitionRequest,
        client: JiraAgileClientProtocol = Depends(get_client),
    ):
        if not settings.agile_is_configured:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Jira não configurado",
            )

        def _envelope(code: int, result: TransitionResult) -> JSONResponse:
            # Mesmo corpo em todo status: o cliente lê `reason`, não o código.
            return JSONResponse(status_code=code, content=result.model_dump())

        try:
            config = _config(client)
            result = service.resolve_transition(client, config, issue_key, payload.target_column)
        except AgileUnavailable as exc:
            failure = TransitionResult(
                applied=False,
                issue_key=issue_key,
                new_status_name=None,
                reason=exc.reason,
                available_transitions=[],
            )
            code = (
                status.HTTP_403_FORBIDDEN
                if exc.reason == "forbidden"
                else status.HTTP_502_BAD_GATEWAY
            )
            return _envelope(code, failure)

        if result.applied:
            # A escrita mudou o board: o cache de leitura precisa cair.
            cache.invalidate_prefix("sprint")
            cache.invalidate_prefix("board")
            return result

        if result.reason == "no_transition":
            return _envelope(status.HTTP_409_CONFLICT, result)
        # `already_there` é 200 com applied: false — nada foi enviado ao Jira.
        return result

    return router
