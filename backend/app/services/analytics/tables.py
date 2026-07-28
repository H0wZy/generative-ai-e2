"""Historical base — three tables mirroring the three Power BI exports.

Column name = the Excel header in snake_case without accents. Each export gets
its own table, column by column: merging them would mean nulls for everything
that only exists in one file, and the two populations are exactly what the
before/after comparison has to keep apart.

Separate metadata from the operational schema on purpose — this is the "before"
picture, not the workflow the automation drives.
"""
from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Index,
    MetaData,
    String,
    Table,
    Text,
)

ANALYTICS_SCHEMA = "analytics"

analytics_metadata = MetaData(schema=ANALYTICS_SCHEMA)


def _chamado_columns() -> list[Column]:
    """Columns common to both Freshservice exports, in Excel order.

    A function, not a shared list: a Column object cannot belong to two tables.
    """
    return [
        Column("id", String, primary_key=True),                  # "ID" (ex: "SR-538944")
        Column("link", String, nullable=True),                   # "Link"
        Column("score", String, nullable=True),                  # "Score"
        Column("status", String, nullable=True),                 # "Status"
        Column("squad", String, nullable=True),                  # "Squad"
        Column("sistema", String, nullable=True),                # "Sistema"
        Column("tecnologia", String, nullable=True),             # "Tecnologia"
        Column("empresa_resp", String, nullable=True),           # "Empresa Resp."
        Column("criacao", Date, nullable=True),                  # "Criação"
        Column("vencimento", Date, nullable=True),               # "Vencimento"
        Column("h_est_ia", Float, nullable=True),                # "H Est. (IA)"
        Column("solicitante", String, nullable=True),            # "Solicitante" — pseudonymized
        Column("agente_tecnico", String, nullable=True),         # "Agente/Técnico" — pseudonymized
        Column("fila", String, nullable=True),                   # "Fila"
        Column("legal_regulat", String, nullable=True),          # "Legal/Regulat."
        Column("prazo_limite_melhoria", String, nullable=True),  # "Prazo limite Melhoria"
        Column("assunto", String, nullable=True),                # "Assunto"
        Column("detalhes", Text, nullable=True),                 # "Detalhes"
        Column("prazo", String, nullable=True),                  # "Prazo"
        Column("impacto", String, nullable=True),                # "Impacto"
        Column("justificativa", String, nullable=True),          # "Justificativa"
        Column("impacto_servico_incidente", String, nullable=True),  # "Impacto Serviço/Incidente"
        Column("ultima_atualizacao", Date, nullable=True),       # "Última Atualização"
        Column("data_resolucao", Date, nullable=True),           # "Data de resolução"
        Column("esforco", String, nullable=True),                # "Esforço"
        Column("classif", String, nullable=True),                # "Classif."
        # ── Application columns (not in the Excel) ──
        Column("synced_at", DateTime(timezone=True), nullable=False),
        # Makes a violation of the anonymization rule detectable by query
        # instead of only by reading the ingestion code.
        Column("anonymized", Boolean, nullable=False, server_default="true"),
    ]


chamados_abertos = Table(
    "chamados_abertos",
    analytics_metadata,
    *_chamado_columns(),
    Column("tempo_em_aberto", String, nullable=True),  # only in the open export
    Index("ix_chamados_abertos_squad", "squad"),
)

chamados_fechados = Table(
    "chamados_fechados",
    analytics_metadata,
    *_chamado_columns(),
    Column("tempo_de_resolucao", String, nullable=True),  # only in the closed export
    Column("sla", String, nullable=True),                 # only in the closed export
    Index("ix_chamados_fechados_squad", "squad"),
)

jira_cards = Table(
    "jira_cards",
    analytics_metadata,
    Column("issue_id", String, primary_key=True),   # "Issue id"
    Column("issue_type", String, nullable=True),    # "Issue Type"
    Column("issue_key", String, nullable=True),     # "Issue key"
    Column("summary", Text, nullable=True),         # "Summary"
    Column("reporter", String, nullable=True),      # "Reporter" — pseudonymized
    Column("reporter_id", String, nullable=True),   # "Reporter Id" — pseudonymized
    Column("priority", String, nullable=True),      # "Priority"
    Column("status", String, nullable=True),        # "Status"
    Column("resolution", String, nullable=True),    # "Resolution"
    Column("created", Date, nullable=True),         # "Created"
    Column("updated", Date, nullable=True),         # "Updated"
    Column("due_date", Date, nullable=True),        # "Due date"
    Column("assignee", String, nullable=True),      # "Assignee" — pseudonymized
    Column("assignee_id", String, nullable=True),   # "Assignee Id" — pseudonymized
    Column("custom_field_tickets_freshservice", String, nullable=True),
    # ── Application columns ──
    # Best-effort link: the 6-digit number extracted from the summary. No FK —
    # the number may point at a ticket outside the exported window.
    Column("freshservice_ticket_id", String, nullable=True),
    Column("synced_at", DateTime(timezone=True), nullable=False),
    Column("anonymized", Boolean, nullable=False, server_default="true"),
    Index("ix_jira_cards_freshservice_ticket_id", "freshservice_ticket_id"),
)
