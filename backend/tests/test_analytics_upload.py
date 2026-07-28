"""Upload detection and the batched upsert, against the real test database."""
from __future__ import annotations

import io

import pandas as pd
import pytest
from sqlalchemy import func, select

from app.services.analytics.excel_ingestion import ingest_dataframe
from app.services.analytics.tables import chamados_abertos, jira_cards
from app.services.analytics.upload_detection import MAX_UPLOAD_BYTES, detect_file_type

FS_ABERTOS_HEADER = ["ID", "Status", "Squad", "Solicitante", "Criação", "Tempo em Aberto"]
JIRA_HEADER = ["Issue key", "Issue id", "Issue Type", "Summary", "Reporter"]


def _csv_bytes(header: list[str], rows: list[list]) -> bytes:
    buffer = io.StringIO()
    pd.DataFrame(rows, columns=header).to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


# ---------------------------------------------------------------------------
# Detection
# ---------------------------------------------------------------------------


def test_detects_kind_ignoring_the_file_name() -> None:
    """Real names ("Data 20260602.xlsx") do not say open or closed."""
    raw = _csv_bytes(JIRA_HEADER, [["SQD04-200", "10001", "Bug", "SAT (143695) ajuste", "Maria"]])
    result = detect_file_type("qualquer-nome-sem-sentido.csv", raw)
    assert result["kind"] == "jira_cards"
    assert result["row_count"] == 1


def test_unrecognized_file_is_flagged_not_raised() -> None:
    raw = _csv_bytes(["coluna_a", "coluna_b"], [["x", "y"]])
    assert detect_file_type("outro.csv", raw)["kind"] == "unknown"


def test_unreadable_file_is_flagged_not_raised() -> None:
    result = detect_file_type("corrompido.xlsx", b"\x00\x01 not a spreadsheet")
    assert result["kind"] == "unreadable"
    assert result["dataframe"] is None


def test_oversized_file_is_rejected_before_parsing() -> None:
    result = detect_file_type("gigante.csv", b"x" * (MAX_UPLOAD_BYTES + 1))
    assert result["kind"] == "too_large"
    assert result["dataframe"] is None


def test_preview_count_excludes_the_footer_row() -> None:
    """The preview must never promise more rows than the commit writes."""
    raw = _csv_bytes(
        FS_ABERTOS_HEADER,
        [
            ["SR-538944", "Aberto", "Squad4", "Maria", "01/06/2026", "3 dias"],
            ["Applied filters:\nStatus 2 is Aberto", "", "", "", "", ""],
        ],
    )
    result = detect_file_type("Data 20260602.csv", raw)
    assert result["kind"] == "fs_abertos"
    assert result["row_count"] == 1


# ---------------------------------------------------------------------------
# Upsert against a real Postgres
# ---------------------------------------------------------------------------


def test_reingesting_the_same_data_updates_and_never_duplicates(engine, db_session) -> None:
    df = pd.DataFrame(
        [{"ID": "SR-1", "Status": "Aberto", "Squad": "Squad4", "Solicitante": "Maria", "Criação": None}]
    )

    inserted, updated = ingest_dataframe(engine, "fs_abertos", df)
    assert (inserted, updated) == (1, 0)

    inserted, updated = ingest_dataframe(engine, "fs_abertos", df)
    assert (inserted, updated) == (0, 1)

    total = db_session.execute(select(func.count()).select_from(chamados_abertos)).scalar_one()
    assert total == 1


def test_upsert_survives_more_rows_than_one_statement_allows(engine, db_session) -> None:
    """Postgres caps a statement at 65,535 bind parameters.

    A single INSERT with every row failed at ~4,000 rows x 17 columns. The
    sample export already carried 3,022 tickets — 77% of that ceiling.
    """
    rows = [
        {"ID": f"SR-{i:06d}", "Status": "Aberto", "Squad": "Squad4", "Solicitante": f"P{i}", "Criação": None}
        for i in range(4001)
    ]
    inserted, updated = ingest_dataframe(engine, "fs_abertos", pd.DataFrame(rows))
    assert inserted == 4001
    assert updated == 0

    total = db_session.execute(select(func.count()).select_from(chamados_abertos)).scalar_one()
    assert total == 4001


def test_persisted_rows_carry_no_original_person_name(engine, db_session) -> None:
    df = pd.DataFrame(
        [{"Issue id": "10001", "Summary": "SAT (143695) ajuste", "Reporter": "Maria Silva"}]
    )
    ingest_dataframe(engine, "jira_cards", df)

    reporters = db_session.execute(select(jira_cards.c.reporter)).scalars().all()
    assert "Maria Silva" not in reporters

    not_anonymized = db_session.execute(
        select(func.count()).select_from(jira_cards).where(jira_cards.c.anonymized.is_(False))
    ).scalar_one()
    assert not_anonymized == 0


def test_zip_bomb_is_rejected_before_parsing() -> None:
    """An xlsx is a zip: the byte ceiling only bounds the COMPRESSED size.

    openpyxl inflates the whole archive to build the DataFrame, so a small
    file with a high compression ratio still exhausts memory at parse time.
    """
    import io
    import zipfile

    from app.services.analytics.upload_detection import MAX_INFLATED_BYTES

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("xl/worksheets/sheet1.xml", b"\x00" * (MAX_INFLATED_BYTES + 1))

    raw = buffer.getvalue()
    assert len(raw) < MAX_UPLOAD_BYTES, "the bomb must pass the byte ceiling"
    assert detect_file_type("bomba.xlsx", raw)["kind"] == "too_large"


def test_a_normal_xlsx_is_not_mistaken_for_a_bomb() -> None:
    import io

    buffer = io.BytesIO()
    pd.DataFrame([{"ID": "SR-1", "Status": "Aberto"}]).to_excel(buffer, index=False)
    assert detect_file_type("normal.xlsx", buffer.getvalue())["kind"] != "too_large"


def test_anonymized_flag_reflects_declared_person_columns() -> None:
    """The audit column must be derived, not hardcoded True.

    Hardcoded, it can never be False — so it always approves itself and would
    not catch a new person column added without being registered.
    """
    from app.services.analytics.anonymization import PERSON_COLUMNS, is_covered

    assert is_covered("chamados_abertos") is True
    assert is_covered("jira_cards") is True
    assert is_covered("tabela_que_nao_existe") is False
    assert set(PERSON_COLUMNS) == {"chamados_abertos", "chamados_fechados", "jira_cards"}
