"""Flow indicators over the historical base, plus the link-coverage comparison.

Ported from the data-receiver Python backend. The functions take a filter
dataclass and an engine; the HTTP layer only wires them.

The one addition is ``link_coverage``: the number this feature exists to move.
"""
from __future__ import annotations

from dataclasses import dataclass, fields

import pandas as pd
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.repositories.schema import JiraIssueLinkRow, TicketRow, WorkflowExecutionRow
from app.services.analytics.enrichment import (
    bucket_by_period,
    fetch_chamados,
    fetch_enriched_cards,
)
from app.services.analytics.excel_ingestion import strip_ticket_prefix
from app.services.analytics.tables import chamados_abertos, chamados_fechados, jira_cards

# "In execution" for Distribuição de Trabalho — a closed list, no fuzzy matching
# ("READY FOR CODE REVIEW" does not count as "CODE REVIEW").
ACTIVE_WORK_STATUSES = {"qa", "in progress", "deploy", "customer approved", "code review"}

# A Jira card still open has an empty Resolution, and there is no native way to
# select "is null" in a <select>. This synthetic label stands for it.
UNRESOLVED_LABEL = "Não resolvido"

TERMINAL_STATUSES = {"done", "canceled", "validated"}


@dataclass
class CommonFilters:
    """The 17 filter dimensions — 11 from the ticket, 6 from the card."""

    # Freshservice (linked ticket)
    squad: str | None = None
    sistema: str | None = None
    tecnologia: str | None = None
    status_chamado: str | None = None
    impacto: str | None = None
    agente_tecnico: str | None = None
    empresa_resp: str | None = None
    fila: str | None = None
    legal_regulat: str | None = None
    prazo: str | None = None
    impacto_servico_incidente: str | None = None
    # Jira (card)
    issue_type: str | None = None
    reporter: str | None = None
    priority: str | None = None
    status: str | None = None
    resolution: str | None = None
    assignee: str | None = None


FS_COLUMNS_IN_CHAMADOS = {
    "squad": "squad",
    "sistema": "sistema",
    "tecnologia": "tecnologia",
    "status_chamado": "status",  # raw column is "status"; renamed only in the join
    "impacto": "impacto",
    "agente_tecnico": "agente_tecnico",
    "empresa_resp": "empresa_resp",
    "fila": "fila",
    "legal_regulat": "legal_regulat",
    "prazo": "prazo",
    "impacto_servico_incidente": "impacto_servico_incidente",
}

FS_COLUMNS_IN_ENRICHED = {**FS_COLUMNS_IN_CHAMADOS, "status_chamado": "status_chamado"}

JIRA_GROUP_COLUMNS = {
    "issue_type": "issue_type",
    "reporter": "reporter",
    "priority": "priority",
    "status": "status",
    "resolution": "resolution",
    "assignee": "assignee",
}


def _matches(df: pd.DataFrame, column: str, value: str) -> pd.Series:
    """Compare a column against a filter value.

    Special case for ``resolution``, where the synthetic label stands for null.
    """
    if column == "resolution" and value == UNRESOLVED_LABEL:
        return df[column].isna()
    return df[column] == value


def group_options(
    df: pd.DataFrame, group_columns: dict[str, str], active: CommonFilters
) -> dict[str, list[str]]:
    """Leave-one-out options: each field narrows by the OTHER active fields of
    its own group, never by itself — otherwise picking a squad made the squad
    dropdown forget every other squad.
    """
    result: dict[str, list[str]] = {}
    for field, column in group_columns.items():
        mask = pd.Series(True, index=df.index)
        for other_field, other_column in group_columns.items():
            if other_field == field:
                continue
            value = getattr(active, other_field)
            if value:
                mask &= _matches(df, other_column, value)

        subset = df[mask]
        values = sorted(subset[column].dropna().unique().tolist())
        if column == "resolution" and subset[column].isna().any():
            values.append(UNRESOLVED_LABEL)
        result[field] = values
    return result


def fetch_filtered(engine: Engine, filters: CommonFilters) -> pd.DataFrame:
    """Enriched cards with every active filter applied together.

    Unlike the dropdown cascade, row filtering crosses both bases freely — this
    is the data the indicators compute on, not a list of options.
    """
    df = fetch_enriched_cards(engine)
    for field, column in {**FS_COLUMNS_IN_ENRICHED, **JIRA_GROUP_COLUMNS}.items():
        value = getattr(filters, field)
        if value:
            df = df[_matches(df, column, value)]
    return df


# ---------------------------------------------------------------------------
# Indicators
# ---------------------------------------------------------------------------


def filter_options(engine: Engine, filters: CommonFilters) -> dict:
    """Real options for the 17 filters — only values present in the data.

    The 11 Freshservice dimensions come from the whole ticket union, not just
    tickets with a linked card: ~73% have no card, and narrowing by the Jira
    side would make their squads and systems vanish from the dropdown.
    """
    chamados = fetch_chamados(engine)
    enriched = fetch_enriched_cards(engine)

    fs_options = group_options(chamados, FS_COLUMNS_IN_CHAMADOS, filters)
    jira_options = group_options(enriched, JIRA_GROUP_COLUMNS, filters)

    return {**fs_options, **jira_options}


def throughput(engine: Engine, filters: CommonFilters, periodicidade: str = "mes") -> dict:
    """Cards delivered per period.

    "Delivered" is ``Resolution == "Done"`` exactly — not ``Status``. The two
    questions are different (where the card is now versus how it ended) and
    they disagree in the data: 291 by resolution against 241 by status.
    """
    df = fetch_filtered(engine, filters)
    total_cards_no_filtro = len(df)

    concluidos = df[(df["resolution"].str.lower() == "done") & df["updated"].notna()].copy()
    total_concluidos = len(concluidos)

    if total_concluidos == 0:
        return {
            "total_concluidos": 0,
            "total_cards_no_filtro": total_cards_no_filtro,
            "por_periodo": [],
            "por_squad_periodo": [],
        }

    concluidos["periodo"] = bucket_by_period(concluidos["updated"], periodicidade)

    por_periodo = (
        concluidos.groupby("periodo").size().reset_index(name="count")
        .sort_values("periodo").to_dict("records")
    )
    # Squad is inherited from the linked ticket, so unlinked cards count in the
    # total but cannot appear in the per-squad breakdown.
    por_squad_periodo = (
        concluidos[concluidos["squad"].notna()]
        .groupby(["periodo", "squad"]).size().reset_index(name="count")
        .sort_values(["periodo", "squad"]).to_dict("records")
    )

    return {
        "total_concluidos": total_concluidos,
        "total_cards_no_filtro": total_cards_no_filtro,
        "por_periodo": por_periodo,
        "por_squad_periodo": por_squad_periodo,
    }


def distribuicao_trabalho(engine: Engine, filters: CommonFilters) -> dict:
    """Work in flight, by assignee and by status.

    ``por_status`` returns every status present, each flagged ``ativo``, so the
    whole flow is visible — not just the five that count as execution.
    """
    df = fetch_filtered(engine, filters)
    com_responsavel = df[df["assignee"].notna()].copy()

    if com_responsavel.empty:
        return {
            "total_ativos": 0,
            "total_recursos": 0,
            "media_por_recurso": None,
            "por_responsavel": [],
            "por_status": [],
        }

    por_status_df = (
        com_responsavel.groupby("status").size().reset_index(name="count")
        .sort_values("count", ascending=False)
    )
    por_status_df["ativo"] = por_status_df["status"].str.lower().isin(ACTIVE_WORK_STATUSES)
    por_status = por_status_df.to_dict("records")

    ativos = com_responsavel[com_responsavel["status"].str.lower().isin(ACTIVE_WORK_STATUSES)]
    total_ativos = len(ativos)

    por_responsavel: list[dict] = []
    total_recursos = 0
    media_por_recurso = None
    if total_ativos > 0:
        por_responsavel = (
            ativos.groupby("assignee").size().reset_index(name="count")
            .sort_values("count", ascending=False).to_dict("records")
        )
        total_recursos = int(ativos["assignee"].nunique())
        media_por_recurso = round(total_ativos / total_recursos, 1) if total_recursos else None

    return {
        "total_ativos": total_ativos,
        "total_recursos": total_recursos,
        "media_por_recurso": media_por_recurso,
        "por_responsavel": por_responsavel,
        "por_status": por_status,
    }


def lead_time(engine: Engine, filters: CommonFilters, periodicidade: str = "mes") -> dict:
    """Days between ticket creation and final delivery.

    Final delivery is when the LAST card linked to that ticket reaches a
    terminal status: an umbrella ticket split into several cards is only
    delivered when the last one finishes. Mean and median both, because the
    distribution has a long tail. ``amostras`` is always the count over the
    whole filtered dataset — never an arbitrary cut.
    """
    df = fetch_filtered(engine, filters)

    concluidos = df[
        df["status"].str.lower().isin(TERMINAL_STATUSES)
        & df["updated"].notna()
        & df["ticket_criacao"].notna()
    ].copy()

    if concluidos.empty:
        return {
            "media_dias": None,
            "mediana_dias": None,
            "amostras": 0,
            "distribuicao": [],
            "por_periodo": [],
        }

    por_chamado = (
        concluidos.groupby("freshservice_ticket_id")
        .agg(entrega_final=("updated", "max"), ticket_criacao=("ticket_criacao", "first"))
        .reset_index()
    )
    por_chamado["dias"] = (
        pd.to_datetime(por_chamado["entrega_final"]) - pd.to_datetime(por_chamado["ticket_criacao"])
    ).dt.days

    bins = [-1, 7, 15, 30, 60, 10**6]
    labels = ["Até 7 dias", "8–15 dias", "16–30 dias", "31–60 dias", "+60 dias"]
    faixas = pd.cut(por_chamado["dias"], bins=bins, labels=labels)
    distribuicao_df = faixas.value_counts().reindex(labels, fill_value=0).reset_index()
    distribuicao_df.columns = ["faixa", "count"]

    por_chamado["periodo"] = bucket_by_period(por_chamado["entrega_final"], periodicidade)
    por_periodo = (
        por_chamado.groupby("periodo")["dias"].mean().round(1)
        .reset_index(name="media_dias").sort_values("periodo").to_dict("records")
    )

    return {
        "media_dias": round(float(por_chamado["dias"].mean()), 1),
        "mediana_dias": round(float(por_chamado["dias"].median()), 1),
        "amostras": int(len(por_chamado)),
        "distribuicao": distribuicao_df.to_dict("records"),
        "por_periodo": por_periodo,
    }


# ---------------------------------------------------------------------------
# The comparison this feature exists to produce
# ---------------------------------------------------------------------------


def link_coverage(engine: Engine, session: Session) -> dict:
    """Link coverage of both populations, side by side.

    ``best_effort`` reconstructs the manual habit: a 6-digit number typed into
    the card summary, counted only when it matches a ticket that actually
    exists in the loaded base.

    ``deterministic`` is what the automation produced: every tombado ticket
    carries a structured link, so coverage is 1.0 by construction — the point
    is that it is *by construction* and not by anyone remembering to type it.
    """
    with engine.connect() as conn:
        total_cards = conn.execute(select(func.count()).select_from(jira_cards)).scalar_one()
        com_vinculo_extraivel = conn.execute(
            select(func.count()).select_from(jira_cards)
            .where(jira_cards.c.freshservice_ticket_id.is_not(None))
        ).scalar_one()

        ticket_ids = set()
        for table in (chamados_abertos, chamados_fechados):
            for raw in conn.execute(select(table.c.id)).scalars():
                ticket_ids.add(strip_ticket_prefix(raw))

        linked_numbers = conn.execute(
            select(jira_cards.c.freshservice_ticket_id)
            .where(jira_cards.c.freshservice_ticket_id.is_not(None))
        ).scalars().all()

    com_chamado_correspondente = sum(1 for n in linked_numbers if n in ticket_ids)

    total_tombados = session.execute(
        select(func.count()).select_from(WorkflowExecutionRow)
        .where(WorkflowExecutionRow.status == "completed")
    ).scalar_one()
    com_vinculo_deterministico = session.execute(
        select(func.count()).select_from(JiraIssueLinkRow)
        .where(JiraIssueLinkRow.link_origin == "deterministic")
    ).scalar_one()

    return {
        "best_effort": {
            "total_cards": total_cards,
            "com_vinculo_extraivel": com_vinculo_extraivel,
            "com_chamado_correspondente": com_chamado_correspondente,
            "cobertura": round(com_chamado_correspondente / total_cards, 3) if total_cards else None,
        },
        "deterministic": {
            "total_tombados": total_tombados,
            "com_vinculo": com_vinculo_deterministico,
            "cobertura": (
                round(com_vinculo_deterministico / total_tombados, 3) if total_tombados else None
            ),
        },
    }


def data_status(engine: Engine) -> dict:
    """Describes the loaded base — no filters. Answers "show upload or dashboard?".

    A separate route from the indicators on purpose: it is the only way to make
    that decision without depending on calls that make no sense on an empty base.
    """
    chamados = fetch_chamados(engine)
    with engine.connect() as conn:
        total_cards = conn.execute(select(func.count()).select_from(jira_cards)).scalar_one()
        ultima_sync = conn.execute(select(func.max(jira_cards.c.synced_at))).scalar_one_or_none()

    total_chamados = len(chamados)
    squads = sorted(chamados["squad"].dropna().unique().tolist()) if total_chamados else []

    periodo = {"de": None, "ate": None}
    if total_chamados and chamados["criacao"].notna().any():
        datas = pd.to_datetime(chamados["criacao"].dropna())
        periodo = {"de": str(datas.min().date()), "ate": str(datas.max().date())}

    return {
        "hasData": bool(total_chamados or total_cards),
        "chamados": total_chamados,
        "cards": total_cards,
        "squads": squads,
        "periodo": periodo,
        "ultimaSincronizacao": ultima_sync.isoformat() if ultima_sync else None,
    }


FILTER_FIELDS = tuple(f.name for f in fields(CommonFilters))
