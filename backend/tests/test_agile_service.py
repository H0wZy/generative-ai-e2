"""Tests for app/services/agile.py — parsing, burndown, WIP and epics."""
from __future__ import annotations

from datetime import date

import pytest

from app.services.agile import (
    build_backlog,
    build_board_columns,
    build_burndown,
    build_sprint,
    parse_board_config,
    parse_issues,
)

_SPRINT = {
    "id": 2,
    "name": "FRESH Sprint 1",
    "state": "active",
    "goal": "",
    "startDate": "2026-07-27T09:00:00.000Z",
    "endDate": "2026-07-31T18:00:00.000Z",
}


def _config(constraint_type: str = "issueCount", estimation_type: str = "field"):
    return parse_board_config(
        2,
        {
            "name": "FRESH board",
            "columnConfig": {
                "columns": [
                    {"name": "A fazer", "statuses": [{"id": "10004"}]},
                    {"name": "Fazendo", "statuses": [{"id": "10005"}], "min": 1, "max": 1},
                    {"name": "Feito", "statuses": [{"id": "10007"}]},
                ],
                "constraintType": constraint_type,
            },
            "estimation": (
                {"type": "field", "field": {"fieldId": "customfield_10016"}}
                if estimation_type == "field"
                else {"type": estimation_type}
            ),
        },
    )


def _issue(key: str, status_id: str, points: float | None, changelog=None, parent=None):
    raw = {
        "key": key,
        "fields": {
            "summary": key,
            "status": {"id": status_id, "name": status_id},
            "customfield_10016": points,
            "labels": [],
            "assignee": None,
            "priority": None,
            "parent": parent,
        },
    }
    if changelog is not None:
        raw["changelog"] = {"histories": changelog}
    return raw


def test_done_comes_from_last_mapped_column_not_the_word_done():
    config = _config()
    assert config.done_status_ids == ["10007"]
    assert config.estimation_field_id == "customfield_10016"


def test_estimation_other_than_field_yields_no_estimation_field():
    config = _config(estimation_type="issueCount")
    assert config.estimation_field_id is None
    items = parse_issues([_issue("A-1", "10004", 5.0)], config)
    assert items[0].points is None


def test_column_without_max_never_flags_over_wip():
    config = parse_board_config(
        2,
        {
            "name": "b",
            "columnConfig": {
                "columns": [{"name": "A fazer", "statuses": [{"id": "10004"}]}],
                "constraintType": "issueCount",
            },
            "estimation": {"type": "none"},
        },
    )
    items = parse_issues([_issue(f"A-{n}", "10004", None) for n in range(5)], config)
    columns = build_board_columns(config, items)
    assert columns[0]["over_wip"] is False


def test_constraint_type_none_disables_over_wip_even_with_max():
    config = _config(constraint_type="none")
    items = parse_issues([_issue("A-1", "10005", 1.0), _issue("A-2", "10005", 1.0)], config)
    columns = build_board_columns(config, items)
    fazendo = next(c for c in columns if c["name"] == "Fazendo")
    assert fazendo["count"] == 2
    assert fazendo["wip_max"] == 1
    assert fazendo["over_wip"] is False


def test_over_wip_fires_when_board_constrains():
    config = _config(constraint_type="issueCount")
    items = parse_issues([_issue("A-1", "10005", 1.0), _issue("A-2", "10005", 1.0)], config)
    fazendo = next(c for c in build_board_columns(config, items) if c["name"] == "Fazendo")
    assert fazendo["over_wip"] is True


def test_empty_sprint_goal_becomes_none():
    config = _config()
    sprint = build_sprint(_SPRINT, [], config, today=date(2026, 7, 28))
    assert sprint.goal is None
    assert sprint.days_left == 3


def test_scope_added_is_split_out_of_committed():
    config = _config()
    issues = [
        _issue("A-1", "10004", 5.0),
        _issue(
            "A-2",
            "10004",
            3.0,
            changelog=[
                {"created": "2026-07-29T10:00:00.000Z", "items": [{"field": "Sprint", "to": "2"}]}
            ],
        ),
    ]
    items = parse_issues(issues, config)
    sprint = build_sprint(_SPRINT, items, config, today=date(2026, 7, 31), issues_raw=issues)

    assert sprint.scope_added_points == 3.0
    # A linha de base é o que havia no início, não o total de hoje.
    assert sprint.committed_points == 5.0
    assert sprint.committed_points + sprint.scope_added_points == 8.0


def test_scope_added_is_zero_without_changelog():
    """Sem changelog não dá para distinguir — zerar é melhor que estimar."""
    config = _config()
    items = parse_issues([_issue("A-1", "10004", 5.0)], config)
    sprint = build_sprint(_SPRINT, items, config, today=date(2026, 7, 31))

    assert sprint.scope_added_points == 0.0
    assert sprint.committed_points == 5.0


def test_burndown_scope_added_raises_the_line_from_entry_day():
    config = _config()
    issues = [
        _issue("A-1", "10004", 5.0),
        _issue(
            "A-2",
            "10004",
            3.0,
            changelog=[
                {
                    "created": "2026-07-29T10:00:00.000Z",
                    "items": [{"field": "Sprint", "to": "2"}],
                }
            ],
        ),
    ]
    series = build_burndown(_SPRINT, issues, config, today=date(2026, 7, 31))

    assert series is not None
    assert series.days[0] == "2026-07-27"
    # Dias 27 e 28 só têm a issue original; a partir do 29 o escopo sobe.
    assert series.actual[0] == 5.0
    assert series.actual[1] == 5.0
    assert series.actual[2] == 8.0
    # A ideal ignora o escopo adicionado — parte do total e desce reta.
    assert series.ideal[0] == 8.0
    assert series.ideal[-1] == 0.0


def test_burndown_future_days_are_not_drawn():
    config = _config()
    series = build_burndown(_SPRINT, [_issue("A-1", "10004", 5.0)], config, today=date(2026, 7, 28))
    assert series is not None
    assert series.actual[2] is None
    assert series.actual[1] == 5.0


def test_burndown_subtracts_points_on_transition_to_done():
    config = _config()
    issues = [
        _issue(
            "A-1",
            "10007",
            5.0,
            changelog=[
                {
                    "created": "2026-07-29T10:00:00.000Z",
                    "items": [{"field": "status", "to": "10007", "toString": "Feito"}],
                }
            ],
        )
    ]
    series = build_burndown(_SPRINT, issues, config, today=date(2026, 7, 31))
    assert series is not None
    assert series.actual[1] == 5.0
    assert series.actual[2] == 0.0


def test_epic_with_zero_points_has_progress_zero_not_nan():
    config = _config()
    parent = {"key": "E-1", "fields": {"summary": "Épico sem estimativa"}}
    items = parse_issues([_issue("A-1", "10004", None, parent=parent)], config)
    view = build_backlog(items, config)

    assert len(view.epics) == 1
    assert view.epics[0].total_points == 0.0
    assert view.epics[0].progress == 0.0


def test_backlog_keeps_jira_rank_order():
    config = _config()
    items = parse_issues(
        [_issue("A-3", "10004", 1.0), _issue("A-1", "10004", 1.0)], config
    )
    assert [item.key for item in items] == ["A-3", "A-1"]
    assert [item.rank for item in items] == [1, 2]


@pytest.mark.parametrize(
    ("name", "expected"),
    [("Ana Lima", "AL"), ("Bruno", "BR"), ("", "?"), ("Ana Paula Sá", "AS")],
)
def test_initials(name, expected):
    from app.services.agile import _initials

    assert _initials(name) == expected
