"""001_initial_workflow

Revision ID: 001
Revises:
Create Date: 2026-07-25
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tickets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("source_system", sa.String(80), nullable=False),
        sa.Column("source_ticket_id", sa.String(80), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("event_id", sa.String(128), nullable=False),
        sa.Column("subject", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("priority", sa.String(20), nullable=False, server_default="medium"),
        sa.Column("category", sa.String(80), nullable=True),
        sa.Column("requester", sa.String(255), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "source_system", "source_ticket_id", "event_type", "event_id",
            name="uq_ticket_event",
        ),
    )

    op.create_table(
        "workflow_executions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_id", UUID(as_uuid=True), sa.ForeignKey("tickets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("internal_correlation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(40), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("squad_id", sa.String(80), nullable=True),
        sa.Column("routing_rule_version", sa.String(80), nullable=True),
        sa.Column("routing_confidence", sa.Float(), nullable=True),
        sa.Column("needs_human_review", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "external_references",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_execution_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_system", sa.String(80), nullable=False),
        sa.Column("external_correlation_id", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_external_refs_source_extid",
        "external_references",
        ["source_system", "external_correlation_id"],
    )

    op.create_table(
        "routing_decisions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_execution_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("rule_version", sa.String(80), nullable=False),
        sa.Column("squad_id", sa.String(80), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("needs_human_review", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_execution_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_executions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("payload_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("claimed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "jira_issue_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "ticket_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tickets.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("jira_issue_key", sa.String(40), nullable=False, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_execution_id",
            UUID(as_uuid=True),
            sa.ForeignKey("workflow_executions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("internal_correlation_id", UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(80), nullable=False),
        sa.Column("details_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    op.drop_table("jira_issue_links")
    op.drop_table("outbox_events")
    op.drop_table("routing_decisions")
    op.drop_index("ix_external_refs_source_extid", table_name="external_references")
    op.drop_table("external_references")
    op.drop_table("workflow_executions")
    op.drop_table("tickets")
