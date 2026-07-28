"""Anonymization of the historical base. A privacy rule, so it gets its own file."""
from __future__ import annotations

import pandas as pd

from app.services.analytics.anonymization import PERSON_COLUMNS, anonymize_rows, pseudonym
from app.services.analytics.excel_ingestion import jira_card_rows_from_df

from datetime import datetime, timezone

NOW = datetime(2026, 7, 27, tzinfo=timezone.utc)


def test_pseudonym_is_stable_across_runs() -> None:
    """Instability would make every re-upload churn the whole table."""
    assert pseudonym("Maria Silva") == pseudonym("Maria Silva")


def test_pseudonym_ignores_case_and_padding() -> None:
    assert pseudonym("Maria Silva") == pseudonym("  maria silva  ")


def test_different_people_get_different_pseudonyms() -> None:
    assert pseudonym("Maria Silva") != pseudonym("Joao Souza")


def test_pseudonym_does_not_contain_the_original() -> None:
    assert "Maria" not in (pseudonym("Maria Silva") or "")
    assert "Silva" not in (pseudonym("Maria Silva") or "")


def test_absence_stays_absence() -> None:
    assert pseudonym(None) is None
    assert pseudonym("") is None
    assert pseudonym("   ") is None


def test_only_person_columns_are_replaced() -> None:
    rows = [{"solicitante": "Maria Silva", "squad": "Squad4", "sistema": "SAP"}]
    out = anonymize_rows(rows, "chamados_abertos")[0]
    assert out["solicitante"] != "Maria Silva"
    assert out["squad"] == "Squad4"
    assert out["sistema"] == "SAP"


def test_every_person_column_of_the_jira_export_is_covered() -> None:
    """reporter_id and assignee_id identify a person as surely as the name."""
    assert set(PERSON_COLUMNS["jira_cards"]) == {"reporter", "reporter_id", "assignee", "assignee_id"}


def test_card_ingestion_anonymizes_before_returning_rows() -> None:
    df = pd.DataFrame(
        [
            {
                "Issue id": "10001",
                "Summary": "SAT (143695) ajuste",
                "Reporter": "Maria Silva",
                "Reporter Id": "user-abc",
                "Assignee": "Joao Souza",
                "Assignee Id": "user-def",
            }
        ]
    )
    row = jira_card_rows_from_df(df, NOW)[0]
    for value in (row["reporter"], row["reporter_id"], row["assignee"], row["assignee_id"]):
        assert value is not None
    assert row["reporter"] != "Maria Silva"
    assert row["reporter_id"] != "user-abc"
    assert row["assignee"] != "Joao Souza"
    assert row["assignee_id"] != "user-def"
    # Free text is deliberately untouched — a known, documented limitation.
    assert row["summary"] == "SAT (143695) ajuste"
