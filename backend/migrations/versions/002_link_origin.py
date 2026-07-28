"""002_link_origin

Adds the squad carried by the source ticket, the origin of the ticket <-> issue
link (the number this whole feature exists to move), and the polling watermark.

Revision ID: 002
Revises: 001
Create Date: 2026-07-27
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # The squad comes filled in from Freshservice. Kept separate from
    # workflow_executions.squad_id, which is what routing *decided*.
    op.add_column("tickets", sa.Column("squad", sa.String(40), nullable=True))

    op.add_column(
        "jira_issue_links",
        sa.Column(
            "link_origin",
            sa.String(20),
            nullable=False,
            server_default="deterministic",
        ),
    )
    op.create_check_constraint(
        "ck_jira_issue_links_link_origin",
        "jira_issue_links",
        "link_origin IN ('deterministic', 'best_effort')",
    )

    # Polling watermark. Lives in the operational schema on purpose: the
    # tombamento must not depend on the historical export being loaded.
    op.create_table(
        "sync_state",
        sa.Column("source", sa.Text(), primary_key=True),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("sync_state")
    op.drop_constraint("ck_jira_issue_links_link_origin", "jira_issue_links", type_="check")
    op.drop_column("jira_issue_links", "link_origin")
    op.drop_column("tickets", "squad")
