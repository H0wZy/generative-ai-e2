"""Flow indicators, the filter cascade, and the link-coverage comparison."""
from __future__ import annotations

import pandas as pd
import pytest

from app.services.analytics import indicators as A
from app.services.analytics.excel_ingestion import ingest_dataframe


@pytest.fixture()
def loaded_base(engine):
    """A small base with the shapes that matter, not a copy of the real export.

    - SR-100001: linked to two cards; the umbrella case for lead time
    - SR-100002: linked to one card, still open
    - SR-100003: no card at all — the ~73% majority
    """
    chamados = pd.DataFrame(
        [
            {
                "ID": "SR-100001", "Status": "Fechado", "Squad": "Squad4", "Sistema": "SAP",
                "Tecnologia": "ABAP", "Solicitante": "Maria", "Criação": pd.Timestamp("2026-01-01"),
                "Tempo de Resolução": "10 dias", "SLA": "Dentro",
            },
            {
                "ID": "SR-100002", "Status": "Aberto", "Squad": "RPA", "Sistema": "Portal",
                "Tecnologia": "Python", "Solicitante": "Joao", "Criação": pd.Timestamp("2026-02-01"),
                "Tempo de Resolução": None, "SLA": None,
            },
            {
                "ID": "SR-100003", "Status": "Aberto", "Squad": "GCP", "Sistema": "Infra",
                "Tecnologia": "Terraform", "Solicitante": "Ana", "Criação": pd.Timestamp("2026-03-01"),
                "Tempo de Resolução": None, "SLA": None,
            },
        ]
    )
    cards = pd.DataFrame(
        [
            {
                "Issue id": "1", "Issue key": "SQD-1", "Issue Type": "Bug",
                "Summary": "SAT (100001) primeira parte", "Reporter": "Maria",
                "Status": "Done", "Resolution": "Done", "Priority": "High",
                "Assignee": "Dev A", "Created": "01/01/2026 10:00", "Updated": "20/01/2026 10:00",
            },
            {
                "Issue id": "2", "Issue key": "SQD-2", "Issue Type": "Task",
                "Summary": "SAT (100001) segunda parte", "Reporter": "Maria",
                "Status": "Done", "Resolution": "Done", "Priority": "Low",
                "Assignee": "Dev B", "Created": "01/01/2026 10:00", "Updated": "31/01/2026 10:00",
            },
            {
                "Issue id": "3", "Issue key": "SQD-3", "Issue Type": "Task",
                "Summary": "SAT (100002) em andamento", "Reporter": "Joao",
                "Status": "In Progress", "Resolution": None, "Priority": "Medium",
                "Assignee": "Dev A", "Created": "01/02/2026 10:00", "Updated": "05/02/2026 10:00",
            },
            {
                "Issue id": "4", "Issue key": "SQD-4", "Issue Type": "Task",
                "Summary": "Tarefa interna sem numero", "Reporter": "Ana",
                "Status": "To Do", "Resolution": None, "Priority": "Low",
                "Assignee": None, "Created": "01/03/2026 10:00", "Updated": "02/03/2026 10:00",
            },
            {
                "Issue id": "5", "Issue key": "SQD-5", "Issue Type": "Bug",
                "Summary": "PAV (277795/357558) ambiguo", "Reporter": "Ana",
                "Status": "Done", "Resolution": "Won't Do", "Priority": "Low",
                "Assignee": "Dev C", "Created": "01/03/2026 10:00", "Updated": "10/03/2026 10:00",
            },
        ]
    )
    ingest_dataframe(engine, "fs_fechados", chamados[chamados["ID"] == "SR-100001"])
    ingest_dataframe(engine, "fs_abertos", chamados[chamados["ID"] != "SR-100001"])
    ingest_dataframe(engine, "jira_cards", cards)
    return engine


NO_FILTER = A.CommonFilters()


# ---------------------------------------------------------------------------
# Throughput
# ---------------------------------------------------------------------------


def test_throughput_counts_resolution_done_not_status_done(loaded_base) -> None:
    """Status and Resolution answer different questions and disagree.

    SQD-5 has Status=Done but Resolution="Won't Do" — it was closed, not
    delivered, so it must not count.
    """
    result = A.throughput(loaded_base, NO_FILTER)
    assert result["total_concluidos"] == 2
    assert result["total_cards_no_filtro"] == 5


def test_throughput_breaks_down_by_inherited_squad(loaded_base) -> None:
    result = A.throughput(loaded_base, NO_FILTER)
    squads = {row["squad"] for row in result["por_squad_periodo"]}
    assert squads == {"Squad4"}


def test_unlinked_card_counts_in_the_total_but_has_no_squad(loaded_base) -> None:
    """A card with no link still exists; it just cannot inherit a squad."""
    df = A.fetch_filtered(loaded_base, NO_FILTER)
    unlinked = df[df["issue_id"] == "4"]
    assert len(unlinked) == 1
    assert pd.isna(unlinked.iloc[0]["squad"])


# ---------------------------------------------------------------------------
# Distribuição de trabalho
# ---------------------------------------------------------------------------


def test_active_work_is_the_closed_status_list_only(loaded_base) -> None:
    result = A.distribuicao_trabalho(loaded_base, NO_FILTER)
    assert result["total_ativos"] == 1  # only SQD-3, In Progress with an assignee


def test_por_status_shows_every_status_flagged_active_or_not(loaded_base) -> None:
    """The whole flow must be visible, not only the five execution statuses."""
    result = A.distribuicao_trabalho(loaded_base, NO_FILTER)
    by_status = {row["status"]: row["ativo"] for row in result["por_status"]}
    assert by_status["In Progress"] is True
    assert by_status["Done"] is False


def test_card_without_assignee_is_excluded(loaded_base) -> None:
    result = A.distribuicao_trabalho(loaded_base, NO_FILTER)
    assert sum(row["count"] for row in result["por_status"]) == 4  # SQD-4 has no assignee


# ---------------------------------------------------------------------------
# Lead time
# ---------------------------------------------------------------------------


def test_lead_time_waits_for_the_last_card_of_an_umbrella_ticket(loaded_base) -> None:
    """SR-100001 has two cards, delivered on 20/01 and 31/01.

    The ticket is only delivered when the last one finishes: 30 days from
    01/01, not 19.
    """
    result = A.lead_time(loaded_base, NO_FILTER)
    assert result["amostras"] == 1
    assert result["media_dias"] == 30.0


def test_lead_time_reports_mean_and_median(loaded_base) -> None:
    """The distribution has a long tail; the mean alone misleads."""
    result = A.lead_time(loaded_base, NO_FILTER)
    assert result["media_dias"] is not None
    assert result["mediana_dias"] is not None


def test_lead_time_amostras_says_how_much_of_the_base_was_used(loaded_base) -> None:
    """Three tickets exist; only one qualifies. The indicator must say so."""
    result = A.lead_time(loaded_base, NO_FILTER)
    assert result["amostras"] == 1


def test_lead_time_on_empty_base_returns_none_not_zero(engine) -> None:
    result = A.lead_time(engine, NO_FILTER)
    assert result["media_dias"] is None
    assert result["amostras"] == 0


# ---------------------------------------------------------------------------
# Filters and cascade
# ---------------------------------------------------------------------------


def test_unresolved_label_filters_null_not_a_string(loaded_base) -> None:
    options = A.filter_options(loaded_base, NO_FILTER)
    assert A.UNRESOLVED_LABEL in options["resolution"]

    filtered = A.fetch_filtered(loaded_base, A.CommonFilters(resolution=A.UNRESOLVED_LABEL))
    assert len(filtered) == 2  # SQD-3 and SQD-4
    assert filtered["resolution"].isna().all()


def test_a_field_never_narrows_its_own_options(loaded_base) -> None:
    """Picking a squad used to make the squad dropdown forget every other one."""
    all_squads = A.filter_options(loaded_base, NO_FILTER)["squad"]
    with_one_picked = A.filter_options(loaded_base, A.CommonFilters(squad="Squad4"))["squad"]
    assert with_one_picked == all_squads


def test_a_field_narrows_the_others_of_its_own_group(loaded_base) -> None:
    narrowed = A.filter_options(loaded_base, A.CommonFilters(sistema="SAP"))
    assert narrowed["tecnologia"] == ["ABAP"]


def test_a_jira_filter_does_not_narrow_the_freshservice_group(loaded_base) -> None:
    """Deliberate: ~73% of tickets have no card and would vanish from the list."""
    all_squads = A.filter_options(loaded_base, NO_FILTER)["squad"]
    with_jira_filter = A.filter_options(loaded_base, A.CommonFilters(issue_type="Bug"))["squad"]
    assert with_jira_filter == all_squads


def test_freshservice_options_come_from_every_ticket_not_only_linked_ones(loaded_base) -> None:
    """SR-100003 (GCP) has no card; its squad must still be selectable."""
    assert "GCP" in A.filter_options(loaded_base, NO_FILTER)["squad"]


def test_filters_from_both_bases_compose_as_intersection(loaded_base) -> None:
    both = A.fetch_filtered(loaded_base, A.CommonFilters(squad="Squad4", issue_type="Bug"))
    assert len(both) == 1
    assert both.iloc[0]["issue_key"] == "SQD-1"


# ---------------------------------------------------------------------------
# The headline number
# ---------------------------------------------------------------------------


def test_link_coverage_separates_the_two_populations(loaded_base, db_session, client) -> None:
    from tests.conftest import synthetic_ticket

    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))
    client.post("/api/v1/workflows/process-next")

    result = A.link_coverage(loaded_base, db_session)

    # Best-effort: 5 cards, 3 with an extractable number, 3 matching a real
    # ticket. SQD-4 has no number and SQD-5 is ambiguous.
    assert result["best_effort"]["total_cards"] == 5
    assert result["best_effort"]["com_vinculo_extraivel"] == 3
    assert result["best_effort"]["com_chamado_correspondente"] == 3

    # Deterministic: linked by construction, not by anyone typing it.
    assert result["deterministic"]["total_tombados"] == 1
    assert result["deterministic"]["cobertura"] == 1.0


def test_link_coverage_on_empty_base_returns_none_not_a_division_error(engine, db_session) -> None:
    result = A.link_coverage(engine, db_session)
    assert result["best_effort"]["cobertura"] is None
    assert result["deterministic"]["cobertura"] is None


# ---------------------------------------------------------------------------
# Data status
# ---------------------------------------------------------------------------


def test_data_status_reports_empty_base_without_failing(engine) -> None:
    result = A.data_status(engine)
    assert result["hasData"] is False
    assert result["chamados"] == 0


def test_data_status_describes_the_whole_loaded_base(loaded_base) -> None:
    result = A.data_status(loaded_base)
    assert result["hasData"] is True
    assert result["chamados"] == 3
    assert result["cards"] == 5
    assert set(result["squads"]) == {"Squad4", "RPA", "GCP"}
    assert result["periodo"]["de"] == "2026-01-01"
