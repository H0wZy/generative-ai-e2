"""004_ticket_resolution_and_conversations

Chamado ao vivo ganha "marcar como concluído" (tickets.resolved_at) e o
assistente ganha conversa persistida por sessão sem login.

Revision ID: 004
Revises: 003
Create Date: 2026-07-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "004"
down_revision = "003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL = chamado aberto. Preenchido = concluído (FR-053).
    op.add_column("tickets", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "assistant_conversations",
        # Gerado no navegador — não há login para amarrar a um usuário.
        sa.Column("session_id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "assistant_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assistant_conversations.session_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sources_json", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_assistant_messages_conversation_created",
        "assistant_messages",
        ["conversation_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_messages_conversation_created", table_name="assistant_messages")
    op.drop_table("assistant_messages")
    op.drop_table("assistant_conversations")
    op.drop_column("tickets", "resolved_at")
