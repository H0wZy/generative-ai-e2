"""003_analytics_schema

The historical base: three tables mirroring the three Power BI exports, column
by column. DDL generated from app/services/analytics/tables.py and frozen here
on purpose — a migration must stay a snapshot, not follow a model that changes
later.

Revision ID: 003
Revises: 002
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op

revision = "003"
down_revision = "002"
branch_labels = None
depends_on = None

_DDL = """
CREATE TABLE analytics.chamados_abertos (
	id VARCHAR NOT NULL, 
	link VARCHAR, 
	score VARCHAR, 
	status VARCHAR, 
	squad VARCHAR, 
	sistema VARCHAR, 
	tecnologia VARCHAR, 
	empresa_resp VARCHAR, 
	criacao DATE, 
	vencimento DATE, 
	h_est_ia FLOAT, 
	solicitante VARCHAR, 
	agente_tecnico VARCHAR, 
	fila VARCHAR, 
	legal_regulat VARCHAR, 
	prazo_limite_melhoria VARCHAR, 
	assunto VARCHAR, 
	detalhes TEXT, 
	prazo VARCHAR, 
	impacto VARCHAR, 
	justificativa VARCHAR, 
	impacto_servico_incidente VARCHAR, 
	ultima_atualizacao DATE, 
	data_resolucao DATE, 
	esforco VARCHAR, 
	classif VARCHAR, 
	synced_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	anonymized BOOLEAN DEFAULT 'true' NOT NULL, 
	tempo_em_aberto VARCHAR, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_chamados_abertos_squad ON analytics.chamados_abertos (squad);
CREATE TABLE analytics.chamados_fechados (
	id VARCHAR NOT NULL, 
	link VARCHAR, 
	score VARCHAR, 
	status VARCHAR, 
	squad VARCHAR, 
	sistema VARCHAR, 
	tecnologia VARCHAR, 
	empresa_resp VARCHAR, 
	criacao DATE, 
	vencimento DATE, 
	h_est_ia FLOAT, 
	solicitante VARCHAR, 
	agente_tecnico VARCHAR, 
	fila VARCHAR, 
	legal_regulat VARCHAR, 
	prazo_limite_melhoria VARCHAR, 
	assunto VARCHAR, 
	detalhes TEXT, 
	prazo VARCHAR, 
	impacto VARCHAR, 
	justificativa VARCHAR, 
	impacto_servico_incidente VARCHAR, 
	ultima_atualizacao DATE, 
	data_resolucao DATE, 
	esforco VARCHAR, 
	classif VARCHAR, 
	synced_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	anonymized BOOLEAN DEFAULT 'true' NOT NULL, 
	tempo_de_resolucao VARCHAR, 
	sla VARCHAR, 
	PRIMARY KEY (id)
);
CREATE INDEX ix_chamados_fechados_squad ON analytics.chamados_fechados (squad);
CREATE TABLE analytics.jira_cards (
	issue_id VARCHAR NOT NULL, 
	issue_type VARCHAR, 
	issue_key VARCHAR, 
	summary TEXT, 
	reporter VARCHAR, 
	reporter_id VARCHAR, 
	priority VARCHAR, 
	status VARCHAR, 
	resolution VARCHAR, 
	created DATE, 
	updated DATE, 
	due_date DATE, 
	assignee VARCHAR, 
	assignee_id VARCHAR, 
	custom_field_tickets_freshservice VARCHAR, 
	freshservice_ticket_id VARCHAR, 
	synced_at TIMESTAMP WITH TIME ZONE NOT NULL, 
	anonymized BOOLEAN DEFAULT 'true' NOT NULL, 
	PRIMARY KEY (issue_id)
);
CREATE INDEX ix_jira_cards_freshservice_ticket_id ON analytics.jira_cards (freshservice_ticket_id);
"""


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS analytics")
    for statement in filter(None, (s.strip() for s in _DDL.split(";"))):
        op.execute(statement)


def downgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS analytics CASCADE")
