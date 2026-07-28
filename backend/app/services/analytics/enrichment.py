"""Joins the historical base: cards enriched with their linked ticket.

Two blocks:

1. ``fetch_chamados`` — open plus closed, with "closed wins" as the tiebreak. A
   ticket that closed between two exports exists in both tables; the closed row
   is the final state.
2. ``fetch_enriched_cards`` — Jira cards joined to the linked ticket through the
   6-digit rule. Squad is an attribute of the TICKET, not of the card: the Jira
   export has no squad column, and deriving one from the issue-key prefix
   produced a Squad3 that does not exist in Freshservice while hiding 11 real
   squads from the filters.
"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import Engine, select

from app.services.analytics.excel_ingestion import strip_ticket_prefix
from app.services.analytics.tables import chamados_abertos, chamados_fechados, jira_cards

# Columns common to both ticket tables that the indicators and filters use.
CHAMADO_COLUMNS = [
    "id",
    "squad",
    "sistema",
    "tecnologia",
    "empresa_resp",
    "status",
    "impacto",
    "agente_tecnico",
    "fila",
    "legal_regulat",
    "prazo",
    "impacto_servico_incidente",
    "criacao",
    "data_resolucao",
]

CARD_COLUMNS = [
    "issue_id",
    "issue_key",
    "issue_type",
    "status",
    "resolution",
    "priority",
    "assignee",
    "reporter",
    "created",
    "updated",
    "freshservice_ticket_id",
]

# Ticket columns renamed only where they genuinely collide with a card column.
_TICKET_RENAME = {
    "id": "ticket_id",
    "status": "status_chamado",
    "criacao": "ticket_criacao",
    "data_resolucao": "ticket_data_resolucao",
}


def fetch_chamados(engine: Engine) -> pd.DataFrame:
    """All tickets, deduplicated by id with the closed row winning."""
    with engine.connect() as conn:
        fechados_rows = conn.execute(
            select(*(chamados_fechados.c[c] for c in CHAMADO_COLUMNS), chamados_fechados.c.sla)
        ).mappings().all()
        abertos_rows = conn.execute(
            select(*(chamados_abertos.c[c] for c in CHAMADO_COLUMNS))
        ).mappings().all()

    fechados_df = pd.DataFrame(fechados_rows, columns=CHAMADO_COLUMNS + ["sla"])
    abertos_df = pd.DataFrame(abertos_rows, columns=CHAMADO_COLUMNS)
    abertos_df["sla"] = None

    fechados_df["origem"] = "fechados"
    abertos_df["origem"] = "abertos"

    if not fechados_df.empty and not abertos_df.empty:
        abertos_df = abertos_df[~abertos_df["id"].isin(set(fechados_df["id"]))]

    return pd.concat([fechados_df, abertos_df], ignore_index=True)


def fetch_enriched_cards(engine: Engine) -> pd.DataFrame:
    """Cards joined to their linked ticket, when the link resolves.

    A card with no valid link keeps the ticket columns as NaN — out of any
    inherited filter, but still counted by indicators that do not need the link.

    No SQL-side filtering on purpose: the leave-one-out cascade has to be able
    to exclude each field from its own narrowing, which only works over the
    whole DataFrame. The base is ~400 cards, so this costs nothing.
    """
    card_stmt = select(*(jira_cards.c[name] for name in CARD_COLUMNS))

    with engine.connect() as conn:
        cards_rows = conn.execute(card_stmt).mappings().all()

    cards_df = pd.DataFrame(cards_rows, columns=CARD_COLUMNS)
    chamados_df = fetch_chamados(engine)

    # Expected columns computed from the real select list, not from the rename
    # dict: a column that is not renamed (fila, squad, ...) would never appear
    # in the values of that dict, and reading it later raised KeyError whenever
    # the cards table was empty.
    enriched_cols = [_TICKET_RENAME.get(c, c) for c in CHAMADO_COLUMNS] + ["sla", "origem"]

    if cards_df.empty or chamados_df.empty:
        for col in enriched_cols:
            cards_df[col] = None
        return cards_df

    chamados_df = chamados_df.copy()
    chamados_df["numeric_id"] = chamados_df["id"].map(strip_ticket_prefix)
    # An SR-/INC- collision on the same number does not occur in the real data,
    # but closed comes first in the concat, so keep="first" preserves it.
    chamados_dedup = (
        chamados_df.drop_duplicates(subset="numeric_id", keep="first")
        .set_index("numeric_id")
        .rename(columns=_TICKET_RENAME)
    )

    return cards_df.join(chamados_dedup, on="freshservice_ticket_id")


def bucket_by_period(dates: pd.Series, periodicidade: str) -> pd.Series:
    """Group a date series into period labels.

    ``semana``/``quinzena`` are anchored on the starting Monday so the labels
    sort chronologically on a chart axis. The fortnight anchor is a fixed, and
    arbitrary, past Monday, only so the 14-day buckets are stable across calls.
    """
    dt = pd.to_datetime(dates)

    if periodicidade == "dia":
        return dt.dt.strftime("%Y-%m-%d")
    if periodicidade == "semana":
        week_start = dt - pd.to_timedelta(dt.dt.dayofweek, unit="D")
        return week_start.dt.strftime("%Y-%m-%d")
    if periodicidade == "quinzena":
        epoch = pd.Timestamp("2020-01-06")  # a Monday; fixed and arbitrary
        days_since_epoch = (dt - epoch).dt.days
        bucket_start = epoch + pd.to_timedelta((days_since_epoch // 14) * 14, unit="D")
        return bucket_start.dt.strftime("%Y-%m-%d")
    if periodicidade == "trimestre":
        return dt.dt.to_period("Q").astype(str)
    return dt.dt.to_period("M").astype(str)  # default: mes
