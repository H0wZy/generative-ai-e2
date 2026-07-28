"""Parsing and link-extraction rules of the historical ingestion — no DB."""
from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import pytest

from app.services.analytics.excel_ingestion import (
    chamado_rows_from_df,
    classify_columns,
    extract_freshservice_ticket_id,
    jira_card_rows_from_df,
    parse_cell_date,
    parse_jira_date,
    strip_ticket_prefix,
)

NOW = datetime(2026, 7, 27, tzinfo=timezone.utc)
_ABERTOS_EXTRA = {"Tempo em Aberto": "tempo_em_aberto"}


# ---------------------------------------------------------------------------
# File classification
# ---------------------------------------------------------------------------


def test_classifies_by_column_signature_not_by_name() -> None:
    fs_common = {"ID", "Status", "Squad", "Solicitante", "Criação"}
    assert classify_columns(fs_common | {"Tempo em Aberto"}) == "fs_abertos"
    assert classify_columns(fs_common | {"SLA", "Tempo de Resolução"}) == "fs_fechados"
    assert classify_columns({"Issue key", "Issue id", "Issue Type", "Summary", "Reporter"}) == "jira_cards"
    assert classify_columns({"foo", "bar"}) == "unknown"


def test_freshservice_signature_alone_is_not_enough() -> None:
    """Without the distinguishing marker there is no way to tell the two apart."""
    assert classify_columns({"ID", "Status", "Squad", "Solicitante", "Criação"}) == "unknown"


# ---------------------------------------------------------------------------
# The 6-digit link rule
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("summary", "expected"),
    [
        ("...em continuidade ao ticket #SR-183490", "183490"),
        ("INC-539824 corrigir fluxo", "539824"),
        ("SAT (143695) Correção Repasse Administrativo", "143695"),
        ("[SAT 143695] Erros na mensagem de alerta", "143695"),
        ("ENTREGA 0 - PEW", None),
        ("SQL p/ Denodo", None),
        ("", None),
    ],
)
def test_extracts_ticket_number_from_summary(summary: str, expected: str | None) -> None:
    assert extract_freshservice_ticket_id(summary) == expected


def test_two_bare_numbers_never_link() -> None:
    """Guessing one of two numbers linked to the wrong ticket in real data."""
    assert extract_freshservice_ticket_id("PAV (277795/357558)") is None


def test_explicit_prefix_wins_over_bare_number() -> None:
    assert extract_freshservice_ticket_id("SR-111111 relacionado a 222222") == "111111"


def test_accepts_invisible_hyphen_variants() -> None:
    """Text pasted from other tools carries non-breaking hyphens and dashes."""
    for dash in ("-", "‐", "‑", "‒", "–", "—"):
        assert extract_freshservice_ticket_id(f"SR{dash}143695 ajuste") == "143695"


def test_strip_prefix_matches_both_sides_of_the_comparison() -> None:
    assert strip_ticket_prefix("SR-143695") == "143695"
    assert strip_ticket_prefix("INC-539824") == "539824"


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------


def test_empty_date_cell_is_none_not_year_48113() -> None:
    """pd.NaT is not a Timestamp but does inherit datetime.

    Without the isna check first, NaT.date() produced a year-48113 sentinel and
    a ghost ticket appeared in the loaded base.
    """
    assert parse_cell_date(pd.NaT) is None
    assert parse_cell_date(None) is None


def test_parses_the_three_date_cell_shapes() -> None:
    assert parse_cell_date(pd.Timestamp("2026-06-02")) == date(2026, 6, 2)
    assert parse_cell_date(datetime(2026, 6, 2, 10, 30)) == date(2026, 6, 2)
    assert parse_cell_date(46175) == date(2026, 6, 2)  # OADate serial


def test_jira_date_uses_the_exact_export_format() -> None:
    assert parse_jira_date("02/06/2026 14:30") == date(2026, 6, 2)
    assert parse_jira_date("") is None
    assert parse_jira_date("not a date") is None


# ---------------------------------------------------------------------------
# Footer row
# ---------------------------------------------------------------------------


def test_discards_the_applied_filters_footer_row() -> None:
    """The export ends with a filter summary that lands in the ID column.

    The cell is not empty, so an "is it blank" check let it through and it
    became a ticket.
    """
    df = pd.DataFrame(
        [
            {"ID": "SR-538944", "Status": "Aberto", "Squad": "Squad4", "Criação": pd.Timestamp("2026-06-01")},
            {"ID": "Applied filters:\nStatus 2 is Aberto\n", "Status": None, "Squad": None, "Criação": None},
        ]
    )
    rows = chamado_rows_from_df(df, NOW, _ABERTOS_EXTRA, "chamados_abertos")
    assert len(rows) == 1
    assert rows[0]["id"] == "SR-538944"


def test_card_row_without_issue_id_is_discarded() -> None:
    df = pd.DataFrame(
        [
            {"Issue id": "10001", "Summary": "SAT (143695) ajuste"},
            {"Issue id": None, "Summary": "linha vazia"},
        ]
    )
    rows = jira_card_rows_from_df(df, NOW)
    assert len(rows) == 1
    assert rows[0]["freshservice_ticket_id"] == "143695"


def test_empty_cell_becomes_null_not_a_placeholder() -> None:
    df = pd.DataFrame([{"ID": "SR-1", "Sistema": None, "Squad": "Squad4"}])
    row = chamado_rows_from_df(df, NOW, _ABERTOS_EXTRA, "chamados_abertos")[0]
    assert row["sistema"] is None
    assert row["squad"] == "Squad4"


def test_ingested_rows_are_marked_anonymized() -> None:
    df = pd.DataFrame([{"ID": "SR-1", "Solicitante": "Maria Silva"}])
    row = chamado_rows_from_df(df, NOW, _ABERTOS_EXTRA, "chamados_abertos")[0]
    assert row["anonymized"] is True
    assert row["solicitante"] != "Maria Silva"
