"""The upload flow over HTTP: preview, commit, and the gate on an empty base."""
from __future__ import annotations

import io

import pandas as pd
from fastapi.testclient import TestClient

FS_ABERTOS_HEADER = ["ID", "Status", "Squad", "Solicitante", "Criação", "Tempo em Aberto"]
JIRA_HEADER = ["Issue key", "Issue id", "Issue Type", "Summary", "Reporter"]


def _csv(header: list[str], rows: list[list]) -> bytes:
    buffer = io.StringIO()
    pd.DataFrame(rows, columns=header).to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def _files() -> list[tuple[str, tuple[str, bytes, str]]]:
    chamados = _csv(
        FS_ABERTOS_HEADER,
        [
            ["SR-100001", "Aberto", "Squad4", "Maria Silva", "01/06/2026", "3 dias"],
            ["SR-100002", "Aberto", "RPA", "Joao Souza", "02/06/2026", "1 dia"],
            ["Applied filters:\nStatus 2 is Aberto", "", "", "", "", ""],
        ],
    )
    cards = _csv(
        JIRA_HEADER,
        [["SQD-1", "10001", "Bug", "SAT (100001) ajuste", "Maria Silva"]],
    )
    return [
        ("files", ("Data 20260602.csv", chamados, "text/csv")),
        ("files", ("relatorio_jira.csv", cards, "text/csv")),
    ]


def test_detect_previews_without_writing_anything(client: TestClient) -> None:
    response = client.post("/api/v1/analytics/upload/detect", files=_files())
    assert response.status_code == 200

    by_name = {f["filename"]: f for f in response.json()["files"]}
    assert by_name["Data 20260602.csv"]["kind"] == "fs_abertos"
    assert by_name["Data 20260602.csv"]["row_count"] == 2  # footer excluded
    assert by_name["relatorio_jira.csv"]["kind"] == "jira_cards"

    # Nothing persisted by a preview.
    assert client.get("/api/v1/analytics/data-status").json()["hasData"] is False


def test_commit_persists_and_a_second_commit_only_updates(client: TestClient) -> None:
    first = client.post("/api/v1/analytics/upload/commit", files=_files()).json()
    assert first["inserted"] == 3  # 2 tickets + 1 card
    assert first["updated"] == 0

    second = client.post("/api/v1/analytics/upload/commit", files=_files()).json()
    assert second["inserted"] == 0
    assert second["updated"] == 3

    status = client.get("/api/v1/analytics/data-status").json()
    assert status["chamados"] == 2
    assert status["cards"] == 1


def test_bad_file_is_skipped_without_taking_the_good_ones_down(client: TestClient) -> None:
    files = _files() + [("files", ("leia-me.txt", b"not a spreadsheet at all", "text/plain"))]

    detected = client.post("/api/v1/analytics/upload/detect", files=files).json()["files"]
    assert {f["kind"] for f in detected if f["filename"] == "leia-me.txt"} == {"unreadable"}

    committed = client.post("/api/v1/analytics/upload/commit", files=files).json()
    assert committed["inserted"] == 3
    assert committed["skipped_files"] == ["leia-me.txt"]


def test_data_status_answers_on_an_empty_base_instead_of_failing(client: TestClient) -> None:
    """This is what decides "show the upload screen or the dashboard".

    It must not depend on indicator calls that make no sense with no data.
    """
    body = client.get("/api/v1/analytics/data-status").json()
    assert body["hasData"] is False
    assert body["chamados"] == 0
    assert body["squads"] == []


def test_indicators_answer_on_an_empty_base(client: TestClient) -> None:
    assert client.get("/api/v1/analytics/throughput").json()["total_concluidos"] == 0
    assert client.get("/api/v1/analytics/lead-time").json()["amostras"] == 0
    assert client.get("/api/v1/analytics/link-coverage").status_code == 200


def test_link_coverage_endpoint_reports_both_populations(client: TestClient) -> None:
    from tests.conftest import synthetic_ticket

    client.post("/api/v1/analytics/upload/commit", files=_files())
    client.post("/api/v1/tickets/ingest", json=synthetic_ticket(squad="SQUAD-04"))
    client.post("/api/v1/workflows/process-next")

    body = client.get("/api/v1/analytics/link-coverage").json()
    assert body["best_effort"]["total_cards"] == 1
    assert body["deterministic"]["cobertura"] == 1.0


def test_upload_response_carries_no_person_name(client: TestClient) -> None:
    """The person columns are pseudonymized before anything is written."""
    client.post("/api/v1/analytics/upload/commit", files=_files())
    options = client.get("/api/v1/analytics/filter-options").json()
    assert "Maria Silva" not in str(options)
    assert "Joao Souza" not in str(options)
