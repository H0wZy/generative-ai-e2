"""Regras de Agile: JSON cru do Jira vira os modelos de `domain/agile.py`.

O cliente HTTP não interpreta nada; toda a lógica de coluna, ponto, burndown,
velocidade e transição está aqui.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from app.domain.agile import (
    BacklogView,
    BoardColumn,
    BoardConfig,
    BurndownSeries,
    Epic,
    Person,
    Sprint,
    TransitionResult,
    VelocityPoint,
    WorkItem,
)
from app.integrations.jira_agile import JiraAgileClientProtocol

# Rótulos que marcam impedimento. Lista fechada: um rótulo qualquer não deve
# poder pintar um card como bloqueado.
_BLOCKED_LABELS = frozenset({"blocked", "bloqueado", "impediment", "impedimento"})

_EPIC_COLORS = ("accent-600", "accent-2-600", "accent-800", "accent-2-800")


# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------


def parse_board_config(board_id: int, raw: dict[str, Any]) -> BoardConfig:
    column_config = raw.get("columnConfig") or {}
    columns = [
        BoardColumn(
            name=column.get("name", ""),
            status_ids=[str(s.get("id")) for s in (column.get("statuses") or [])],
            wip_min=column.get("min"),
            wip_max=column.get("max"),
        )
        for column in (column_config.get("columns") or [])
    ]

    estimation = raw.get("estimation") or {}
    # `type` pode ser "none" ou "issueCount"; só "field" traz fieldId.
    estimation_field = (
        (estimation.get("field") or {}).get("fieldId")
        if estimation.get("type") == "field"
        else None
    )

    # "Done" é a ÚLTIMA coluna mapeada, não a coluna chamada "Done": o board
    # real tem colunas em português (research.md R12b).
    mapped = [c for c in columns if c.status_ids]
    done_status_ids = mapped[-1].status_ids if mapped else []

    return BoardConfig(
        board_id=board_id,
        name=raw.get("name", ""),
        columns=columns,
        constraint_type=column_config.get("constraintType", "none"),
        estimation_field_id=estimation_field,
        done_status_ids=done_status_ids,
    )


def column_for_status(config: BoardConfig, status_id: str) -> str | None:
    for column in config.columns:
        if status_id in column.status_ids:
            return column.name
    return None


# ---------------------------------------------------------------------------
# Issues
# ---------------------------------------------------------------------------


def _initials(name: str) -> str:
    parts = [p for p in name.split() if p]
    if not parts:
        return "?"
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


def _person(raw: dict[str, Any] | None) -> Person | None:
    if not raw:
        return None
    name = raw.get("displayName") or "Sem nome"
    return Person(display_name=name, initials=_initials(name))


def _points(fields: dict[str, Any], estimation_field_id: str | None) -> float | None:
    if not estimation_field_id:
        return None
    value = fields.get(estimation_field_id)
    return float(value) if isinstance(value, (int, float)) else None


def parse_issue(raw: dict[str, Any], config: BoardConfig, rank: int) -> WorkItem:
    fields = raw.get("fields") or {}
    status = fields.get("status") or {}
    status_id = str(status.get("id", ""))
    parent = fields.get("parent") or {}
    labels = list(fields.get("labels") or [])
    blocked = [label for label in labels if label.lower() in _BLOCKED_LABELS]

    return WorkItem(
        key=raw.get("key", ""),
        title=fields.get("summary", ""),
        status_id=status_id,
        status_name=status.get("name", ""),
        column=column_for_status(config, status_id),
        points=_points(fields, config.estimation_field_id),
        labels=labels,
        priority=(fields.get("priority") or {}).get("name"),
        assignee=_person(fields.get("assignee")),
        epic_key=parent.get("key"),
        epic_name=(parent.get("fields") or {}).get("summary"),
        rank=rank,
        blocked_reason=blocked[0] if blocked else None,
    )


def parse_issues(raws: list[dict[str, Any]], config: BoardConfig) -> list[WorkItem]:
    return [parse_issue(raw, config, rank) for rank, raw in enumerate(raws, start=1)]


# ---------------------------------------------------------------------------
# Colunas do quadro
# ---------------------------------------------------------------------------


def build_board_columns(config: BoardConfig, items: list[WorkItem]) -> list[dict[str, Any]]:
    columns: list[dict[str, Any]] = []
    for column in config.columns:
        cards = [item for item in items if item.column == column.name]
        # `constraintType: "none"` significa que o board não impõe limite —
        # nesse caso `over_wip` nunca acende, mesmo com `max` preenchido.
        over_wip = (
            config.constraint_type != "none"
            and column.wip_max is not None
            and len(cards) > column.wip_max
        )
        columns.append(
            {
                "name": column.name,
                "wip_min": column.wip_min,
                "wip_max": column.wip_max,
                "over_wip": over_wip,
                "count": len(cards),
                "cards": [card.model_dump() for card in cards],
            }
        )
    return columns


# ---------------------------------------------------------------------------
# Sprint
# ---------------------------------------------------------------------------


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def entry_days(
    issues_raw: list[dict[str, Any]], start_day: date
) -> dict[str, date]:
    """Dia em que cada issue entrou no sprint, pelo changelog do campo Sprint.

    Quem não tem registro de entrada estava lá desde o início.
    """
    entered: dict[str, date] = {}
    for raw in issues_raw:
        key = raw.get("key", "")
        entered[key] = start_day
        for history in (raw.get("changelog") or {}).get("histories") or []:
            when = _parse_dt(history.get("created"))
            if when is None:
                continue
            for change in history.get("items") or []:
                if (change.get("field") or "").lower() == "sprint" and when.date() > start_day:
                    entered[key] = when.date()
    return entered


def build_sprint(
    raw: dict[str, Any],
    items: list[WorkItem],
    config: BoardConfig,
    today: date | None = None,
    issues_raw: list[dict[str, Any]] | None = None,
) -> Sprint:
    end = _parse_dt(raw.get("endDate"))
    start = _parse_dt(raw.get("startDate"))
    reference = today or datetime.now(timezone.utc).date()
    days_left = max(0, (end.date() - reference).days) if end else 0

    total = sum(item.points or 0.0 for item in items)
    completed = sum(
        item.points or 0.0 for item in items if item.status_id in config.done_status_ids
    )

    # Escopo adicionado = pontos das issues que entraram depois do início.
    # Sem changelog não dá para distinguir, e zerar é melhor que estimar.
    scope_added = 0.0
    if issues_raw is not None and start is not None:
        entered = entry_days(issues_raw, start.date())
        by_key = {item.key: item.points or 0.0 for item in items}
        scope_added = sum(
            by_key.get(key, 0.0) for key, day in entered.items() if day > start.date()
        )

    # `committed` é a linha de base do início do sprint, não o total de hoje —
    # é o que faz `committed + scope_added` bater com o que está no board.
    committed = total - scope_added

    return Sprint(
        id=raw.get("id", 0),
        name=raw.get("name", ""),
        # O Jira devolve "" quando não há objetivo — não é objetivo vazio, é
        # ausência de objetivo (research.md R12b).
        goal=raw.get("goal") or None,
        state=raw.get("state", "active"),
        start_date=raw.get("startDate"),
        end_date=raw.get("endDate"),
        days_left=days_left,
        committed_points=committed,
        completed_points=completed,
        scope_added_points=scope_added,
    )


# ---------------------------------------------------------------------------
# Burndown (research.md R3)
# ---------------------------------------------------------------------------


def build_burndown(
    sprint_raw: dict[str, Any],
    issues_raw: list[dict[str, Any]],
    config: BoardConfig,
    today: date | None = None,
) -> BurndownSeries | None:
    start = _parse_dt(sprint_raw.get("startDate"))
    end = _parse_dt(sprint_raw.get("endDate"))
    if start is None or end is None:
        return None

    start_day, end_day = start.date(), end.date()
    reference = today or datetime.now(timezone.utc).date()
    span = (end_day - start_day).days
    if span < 0:
        return None
    days = [start_day + timedelta(days=offset) for offset in range(span + 1)]

    # Escopo adicionado: a issue só entra na curva a partir do dia de entrada.
    entered = entry_days(issues_raw, start_day)
    done_on: dict[str, date] = {}
    points: dict[str, float] = {}

    for raw in issues_raw:
        key = raw.get("key", "")
        points[key] = _points(raw.get("fields") or {}, config.estimation_field_id) or 0.0

        for history in (raw.get("changelog") or {}).get("histories") or []:
            when = _parse_dt(history.get("created"))
            if when is None:
                continue
            for change in history.get("items") or []:
                if (change.get("field") or "").lower() == "status" and str(
                    change.get("to")
                ) in config.done_status_ids:
                    done_on[key] = when.date()

    # Se a issue está em Done hoje mas não há registro de quando, conta desde
    # o início — melhor que sumir da curva.
    for raw in issues_raw:
        key = raw.get("key", "")
        status_id = str(((raw.get("fields") or {}).get("status") or {}).get("id", ""))
        if status_id in config.done_status_ids and key not in done_on:
            done_on[key] = start_day

    total_committed = sum(points.values())
    ideal = [
        round(total_committed * (1 - index / span), 2) if span else 0.0
        for index in range(span + 1)
    ]

    actual: list[float | None] = []
    for day in days:
        if day > reference:
            actual.append(None)
            continue
        scope = sum(value for key, value in points.items() if entered[key] <= day)
        burned = sum(
            value for key, value in points.items() if key in done_on and done_on[key] <= day
        )
        actual.append(round(scope - burned, 2))

    return BurndownSeries(
        days=[day.isoformat() for day in days],
        ideal=ideal,
        actual=actual,
    )


# ---------------------------------------------------------------------------
# Velocidade
# ---------------------------------------------------------------------------


def build_velocity(
    sprints_with_issues: list[tuple[dict[str, Any], list[WorkItem]]],
    config: BoardConfig,
) -> list[VelocityPoint]:
    """Últimos sprints fechados, mais antigo primeiro."""
    points: list[VelocityPoint] = []
    for raw, items in sprints_with_issues:
        committed = sum(item.points or 0.0 for item in items)
        completed = sum(
            item.points or 0.0 for item in items if item.status_id in config.done_status_ids
        )
        points.append(
            VelocityPoint(
                sprint_name=raw.get("name", ""),
                committed=committed,
                completed=completed,
            )
        )
    return points


# ---------------------------------------------------------------------------
# Épicos e backlog
# ---------------------------------------------------------------------------


def build_backlog(items: list[WorkItem], config: BoardConfig) -> BacklogView:
    epics: dict[str, Epic] = {}
    for item in items:
        if not item.epic_key:
            continue
        epic = epics.get(item.epic_key)
        if epic is None:
            epic = Epic(
                key=item.epic_key,
                name=item.epic_name or item.epic_key,
                color=_EPIC_COLORS[len(epics) % len(_EPIC_COLORS)],
                total_points=0.0,
                done_points=0.0,
                progress=0.0,
            )
            epics[item.epic_key] = epic
        epic.total_points += item.points or 0.0
        if item.status_id in config.done_status_ids:
            epic.done_points += item.points or 0.0

    for epic in epics.values():
        # Épico sem estimativa não tem progresso — divisão por zero seria NaN
        # na tela.
        epic.progress = (
            round(epic.done_points / epic.total_points, 4) if epic.total_points else 0.0
        )

    return BacklogView(epics=list(epics.values()), items=items)


# ---------------------------------------------------------------------------
# Transição (research.md R4 + R12b)
# ---------------------------------------------------------------------------


def resolve_transition(
    client: JiraAgileClientProtocol,
    config: BoardConfig,
    issue_key: str,
    target_column: str,
) -> TransitionResult:
    target = next((c for c in config.columns if c.name == target_column), None)
    if target is None or not target.status_ids:
        return TransitionResult(
            applied=False,
            issue_key=issue_key,
            new_status_name=None,
            reason="no_transition",
            available_transitions=[c.name for c in config.columns if c.status_ids],
        )

    current = client.get_issue_status(issue_key)
    # O Jira OFERECE transição para o status atual (medido no board FRESH), por
    # isso a guarda é comparação de estado, não ausência de transição.
    if str(current.get("id")) in target.status_ids:
        return TransitionResult(
            applied=False,
            issue_key=issue_key,
            new_status_name=current.get("name"),
            reason="already_there",
            available_transitions=[],
        )

    transitions = client.get_transitions(issue_key)
    match = next(
        (t for t in transitions if str((t.get("to") or {}).get("id")) in target.status_ids),
        None,
    )
    if match is None:
        return TransitionResult(
            applied=False,
            issue_key=issue_key,
            new_status_name=None,
            reason="no_transition",
            available_transitions=[
                (t.get("to") or {}).get("name") or t.get("name", "") for t in transitions
            ],
        )

    client.apply_transition(issue_key, str(match.get("id")))
    # Status relido do Jira, não o esperado — é o que SC-013 verifica.
    confirmed = client.get_issue_status(issue_key)
    return TransitionResult(
        applied=True,
        issue_key=issue_key,
        new_status_name=confirmed.get("name"),
        reason=None,
        available_transitions=[],
    )
