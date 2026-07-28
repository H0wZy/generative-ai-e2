"""Ingestion of the Power BI exports into the analytics schema.

Ported from the data-receiver Python backend, which was already validated
against the real files and a real Postgres. What changed: the target schema,
and every row now passes through anonymization before it is written.

File type is recognized by the column signature of the header — never by the
file name. The real names ("Data 20260602.xlsx") do not reliably say whether
the export is of open or closed tickets.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import Connection, Engine, Table, literal_column
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.services.analytics.anonymization import anonymize_rows, is_covered
from app.services.analytics.tables import chamados_abertos, chamados_fechados, jira_cards

# ── Link extraction (the 6-digit business rule) ──────────────────────────────
# An explicit SR-/INC- prefix wins over a bare 6-digit number. The hyphen class
# covers ASCII plus the Unicode variants that show up in summaries pasted from
# other tools.
_PREFIXED_ID_RE = re.compile(r"(?:SR|INC)[-‐‑‒–—]?\s*(\d{6})", re.IGNORECASE)
_BARE_ID_RE = re.compile(r"\b(\d{6})\b")

# The Freshservice export ends with a footer row summarizing the applied
# filters, and it lands in the ID column. Without this check it becomes a fake
# ticket — it once produced a ticket dated year 48113.
_TICKET_ID_RE = re.compile(r"^[A-Za-z]+-\d+$")

_JIRA_DATE_FORMATS = ("%d/%m/%Y %H:%M", "%d/%m/%Y")

# ── Column signatures ────────────────────────────────────────────────────────

FS_SIGNATURE_COLUMNS = {"ID", "Status", "Squad", "Solicitante", "Criação"}
FS_ABERTOS_MARKER = "Tempo em Aberto"
FS_FECHADOS_MARKERS = {"Tempo de Resolução", "SLA"}
JIRA_SIGNATURE_COLUMNS = {"Issue key", "Issue id", "Issue Type", "Summary", "Reporter"}


def classify_columns(columns: set[str]) -> str:
    """Return which source file a set of columns represents.

    One of ``jira_cards``, ``fs_abertos``, ``fs_fechados`` or ``unknown``.
    """
    if JIRA_SIGNATURE_COLUMNS <= columns:
        return "jira_cards"
    if FS_SIGNATURE_COLUMNS <= columns:
        if FS_FECHADOS_MARKERS & columns:
            return "fs_fechados"
        if FS_ABERTOS_MARKER in columns:
            return "fs_abertos"
    return "unknown"


# ── Dates ────────────────────────────────────────────────────────────────────


def parse_cell_date(value: object) -> date | None:
    """Parse an xlsx date cell: Timestamp, datetime, OADate serial or string.

    ``pd.isna`` comes first: ``pd.NaT`` is not a ``Timestamp`` but does inherit
    from ``datetime``, so without this check an empty date cell fell into the
    datetime branch and ``NaT.date()`` returned a year-48113 sentinel.
    """
    if pd.isna(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, (int, float)):
        # OADate epoch: 1899-12-30.
        return (datetime(1899, 12, 30) + pd.Timedelta(days=value)).date()
    if isinstance(value, str):
        return _try_parse_flexible_date(value)
    return None


def _try_parse_flexible_date(value: str) -> date | None:
    value = value.strip()
    if not value:
        return None
    for fmt in _JIRA_DATE_FORMATS:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    try:
        return pd.to_datetime(value, dayfirst=True).date()
    except (ValueError, TypeError):
        return None


def parse_jira_date(value: str | None) -> date | None:
    """The Jira export uses ``dd/MM/yyyy HH:mm``. Exact format, no loose fallback."""
    if not value or not value.strip():
        return None
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y %H:%M").date()
    except ValueError:
        return None


# ── Best-effort link ─────────────────────────────────────────────────────────


def strip_ticket_prefix(source_id: str) -> str:
    """``"SR-143695"`` -> ``"143695"``. The Jira text never says SR or INC."""
    _, _, tail = source_id.partition("-")
    return tail or source_id


def extract_freshservice_ticket_id(summary: str) -> str | None:
    """Extract the Freshservice ticket number cited in a Jira summary.

    Two or more distinct bare numbers with no explicit prefix is ambiguous —
    returns ``None`` rather than risk linking to the wrong ticket.
    """
    if not summary:
        return None
    prefixed = _PREFIXED_ID_RE.search(summary)
    if prefixed:
        return prefixed.group(1)

    distinct = list(dict.fromkeys(_BARE_ID_RE.findall(summary)))
    return distinct[0] if len(distinct) == 1 else None


# ── Cell helpers ─────────────────────────────────────────────────────────────


def _cell_str(value: object) -> str | None:
    if pd.isna(value):
        return None
    return str(value)


def _cell_float(value: object) -> float | None:
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ── Batched upsert ───────────────────────────────────────────────────────────

# Postgres caps a statement at 65,535 bind parameters. A single INSERT with
# every row blows through that on an export only slightly larger than the
# sample: 59,500 params pass, 68,000 fail. 1,000 rows x ~30 columns leaves
# ample headroom.
_UPSERT_CHUNK_SIZE = 1000


def _upsert(conn: Connection, table: Table, rows: list[dict]) -> tuple[int, int]:
    """Insert or update by primary key, in chunks, inside the caller's transaction.

    Uses the Postgres ``xmax = 0`` trick to tell insert from update per row.
    """
    if not rows:
        return 0, 0

    pk_name = next(iter(table.primary_key.columns)).name
    update_cols = [c.name for c in table.columns if c.name != pk_name]

    inserted = 0
    updated = 0
    for start in range(0, len(rows), _UPSERT_CHUNK_SIZE):
        chunk = rows[start : start + _UPSERT_CHUNK_SIZE]
        stmt = pg_insert(table).values(chunk)
        stmt = stmt.on_conflict_do_update(
            index_elements=[pk_name],
            set_={name: stmt.excluded[name] for name in update_cols},
        ).returning(literal_column("(xmax = 0)").label("inserted"))

        result = conn.execute(stmt).all()
        chunk_inserted = sum(1 for row in result if row.inserted)
        inserted += chunk_inserted
        updated += len(result) - chunk_inserted

    return inserted, updated


# ── Freshservice mapping ─────────────────────────────────────────────────────

_CHAMADO_TEXT_COLUMNS = {
    "Link": "link",
    "Score": "score",
    "Status": "status",
    "Squad": "squad",
    "Sistema": "sistema",
    "Tecnologia": "tecnologia",
    "Empresa Resp.": "empresa_resp",
    "Solicitante": "solicitante",
    "Agente/Técnico": "agente_tecnico",
    "Fila": "fila",
    "Legal/Regulat.": "legal_regulat",
    "Prazo limite Melhoria": "prazo_limite_melhoria",
    "Assunto": "assunto",
    "Detalhes": "detalhes",
    "Prazo": "prazo",
    "Impacto": "impacto",
    "Justificativa": "justificativa",
    "Impacto Serviço/Incidente": "impacto_servico_incidente",
    "Esforço": "esforco",
    "Classif.": "classif",
}
_CHAMADO_DATE_COLUMNS = {
    "Criação": "criacao",
    "Vencimento": "vencimento",
    "Última Atualização": "ultima_atualizacao",
    "Data de resolução": "data_resolucao",
}
_ABERTOS_EXTRA = {"Tempo em Aberto": "tempo_em_aberto"}
_FECHADOS_EXTRA = {"Tempo de Resolução": "tempo_de_resolucao", "SLA": "sla"}


def chamado_rows_from_df(
    df: pd.DataFrame, now: datetime, extra_map: dict[str, str], table_name: str
) -> list[dict]:
    """Valid rows from a Freshservice DataFrame, ready to upsert and anonymized."""
    rows = []
    for row in df.to_dict("records"):
        get = row.get
        chamado_id = _cell_str(get("ID"))
        if not chamado_id or not _TICKET_ID_RE.match(chamado_id):
            continue
        values: dict = {"id": chamado_id, "synced_at": now, "anonymized": is_covered(table_name)}
        for excel_col, db_col in _CHAMADO_TEXT_COLUMNS.items():
            values[db_col] = _cell_str(get(excel_col))
        for excel_col, db_col in _CHAMADO_DATE_COLUMNS.items():
            values[db_col] = parse_cell_date(get(excel_col))
        values["h_est_ia"] = _cell_float(get("H Est. (IA)"))
        for excel_col, db_col in extra_map.items():
            values[db_col] = _cell_str(get(excel_col))
        rows.append(values)
    return anonymize_rows(rows, table_name)


def jira_card_rows_from_df(df: pd.DataFrame, now: datetime) -> list[dict]:
    """Valid rows from the Jira CSV, ready to upsert and anonymized."""
    rows = []
    for row in df.to_dict("records"):
        get = row.get
        issue_id = _cell_str(get("Issue id"))
        if not issue_id or not issue_id.strip():
            continue
        summary = _cell_str(get("Summary")) or ""

        def txt(col: str) -> str | None:
            value = _cell_str(get(col))
            return value if value and value.strip() else None

        rows.append(
            {
                "issue_id": issue_id,
                "issue_type": txt("Issue Type"),
                "issue_key": txt("Issue key"),
                "summary": summary,
                "reporter": txt("Reporter"),
                "reporter_id": txt("Reporter Id"),
                "priority": txt("Priority"),
                "status": txt("Status"),
                "resolution": txt("Resolution"),
                "created": parse_jira_date(_cell_str(get("Created"))),
                "updated": parse_jira_date(_cell_str(get("Updated"))),
                "due_date": parse_jira_date(_cell_str(get("Due date"))),
                "assignee": txt("Assignee"),
                "assignee_id": txt("Assignee Id"),
                "custom_field_tickets_freshservice": txt("Custom field (Tickets do Freshservice)"),
                "freshservice_ticket_id": extract_freshservice_ticket_id(summary),
                "synced_at": now,
                "anonymized": is_covered("jira_cards"),
            }
        )
    return anonymize_rows(rows, "jira_cards")


# ── Entry points ─────────────────────────────────────────────────────────────


def rows_for_kind(kind: str, df: pd.DataFrame, now: datetime | None = None) -> list[dict]:
    """Rows a given file kind would write. Used by both the preview and the commit,
    so the previewed count can never overstate what the commit persists."""
    now = now or datetime.now(timezone.utc)
    if kind == "fs_abertos":
        return chamado_rows_from_df(df, now, _ABERTOS_EXTRA, "chamados_abertos")
    if kind == "fs_fechados":
        return chamado_rows_from_df(df, now, _FECHADOS_EXTRA, "chamados_fechados")
    if kind == "jira_cards":
        return jira_card_rows_from_df(df, now)
    return []


_TABLE_BY_KIND = {
    "fs_abertos": chamados_abertos,
    "fs_fechados": chamados_fechados,
    "jira_cards": jira_cards,
}


def ingest_dataframe(engine: Engine, kind: str, df: pd.DataFrame) -> tuple[int, int]:
    """Upsert one already-classified DataFrame. One file, one transaction."""
    table = _TABLE_BY_KIND[kind]
    rows = rows_for_kind(kind, df)
    with engine.begin() as conn:
        return _upsert(conn, table, rows)


def read_dataframe(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, encoding="utf-8-sig", dtype=str, keep_default_na=False)
    return pd.read_excel(path, engine="openpyxl")


def ingest_from_directory(engine: Engine, directory: Path) -> dict:
    """Read every xlsx/csv in a directory, classify each, upsert into its table.

    Unrecognized files are skipped — the export directory also holds reference
    screenshots.
    """
    summary = {"chamados_inserted": 0, "chamados_updated": 0, "cards_inserted": 0, "cards_updated": 0}

    for file in sorted(directory.glob("*.xlsx")) + sorted(directory.glob("*.csv")):
        df = read_dataframe(file)
        kind = classify_columns(set(df.columns))
        if kind == "unknown":
            continue
        inserted, updated = ingest_dataframe(engine, kind, df)
        if kind == "jira_cards":
            summary["cards_inserted"] += inserted
            summary["cards_updated"] += updated
        else:
            summary["chamados_inserted"] += inserted
            summary["chamados_updated"] += updated

    return summary
