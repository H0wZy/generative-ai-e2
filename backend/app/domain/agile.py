"""Agile domain — projeções sobre o Jira, sem persistência.

Nenhum destes modelos vira tabela: são a forma da resposta HTTP. Ver
specs/002-unified-itsm-agile-ui/data-model.md seção 2.
"""
from __future__ import annotations

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel

T = TypeVar("T")

AvailabilityReason = Literal[
    "not_configured",
    "unauthorized",
    "forbidden",
    "unavailable",
    "rate_limited",
    "no_transition",
    "already_there",
]


class Envelope(BaseModel, Generic[T]):
    available: bool
    reason: AvailabilityReason | None = None
    detail: str | None = None
    data: T | None = None


class BoardColumn(BaseModel):
    name: str
    status_ids: list[str]
    wip_min: int | None = None
    wip_max: int | None = None
    over_wip: bool = False


class BoardConfig(BaseModel):
    board_id: int
    name: str
    columns: list[BoardColumn]
    constraint_type: Literal["none", "issueCount", "issueCountExclSubs"]
    estimation_field_id: str | None
    # Derivado da ÚLTIMA coluna mapeada, não da string "Done": o board real
    # tem colunas em português (research.md R12b).
    done_status_ids: list[str]


class Sprint(BaseModel):
    id: int
    name: str
    # `goal` vem como string vazia do Jira, não None — normalizado aqui.
    goal: str | None
    state: Literal["active", "closed", "future"]
    start_date: str | None
    end_date: str | None
    days_left: int
    committed_points: float
    completed_points: float
    scope_added_points: float


class Person(BaseModel):
    display_name: str
    initials: str
    # Buscar avatar do Jira exigiria proxy autenticado no backend; as iniciais
    # resolvem a identificação sem essa peça.
    avatar_url: None = None


class WorkItem(BaseModel):
    key: str
    title: str
    status_id: str
    status_name: str
    column: str | None
    points: float | None
    labels: list[str]
    priority: str | None
    assignee: Person | None
    epic_key: str | None
    epic_name: str | None
    rank: int
    blocked_days: int | None = None
    blocked_reason: str | None = None


class Epic(BaseModel):
    key: str
    name: str
    color: str
    total_points: float
    done_points: float
    progress: float


class BurndownSeries(BaseModel):
    days: list[str]
    ideal: list[float]
    # `None` = dia ainda não aconteceu; a linha real não é desenhada ali.
    actual: list[float | None]


class VelocityPoint(BaseModel):
    sprint_name: str
    committed: float
    completed: float


class SprintDashboard(BaseModel):
    board: dict[str, object]
    sprint: Sprint | None
    burndown: BurndownSeries | None
    velocity: list[VelocityPoint]
    blocked: list[WorkItem] | None


class BacklogView(BaseModel):
    epics: list[Epic]
    items: list[WorkItem]


class BoardView(BaseModel):
    constraint_type: str
    columns: list[dict[str, object]]


class TransitionRequest(BaseModel):
    target_column: str


class TransitionResult(BaseModel):
    applied: bool
    issue_key: str
    new_status_name: str | None
    reason: AvailabilityReason | None
    available_transitions: list[str]
