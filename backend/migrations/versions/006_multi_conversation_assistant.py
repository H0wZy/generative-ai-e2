"""006_multi_conversation_assistant

O assistente ganha várias conversas nomeadas por sessão (era uma conversa
única por `session_id`). `assistant_conversations` ganha `id` como PK própria,
`session_id` vira coluna indexada (não-PK), mais `title` e `updated_at`.
Sem dado de produção a preservar (feature pré-lançamento) — dropa e recria em
vez de migrar linha a linha.

Revision ID: 006
Revises: 005
Create Date: 2026-07-30
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "006"
down_revision = "005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_table("assistant_messages")
    op.drop_table("assistant_conversations")

    op.create_table(
        "assistant_conversations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        # Gerado no navegador — não há login para amarrar a um usuário.
        sa.Column("session_id", UUID(as_uuid=True), nullable=False),
        # Vazio até a primeira mensagem (título vem da pergunta do usuário).
        sa.Column("title", sa.String(200), nullable=False, server_default=""),
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
    op.create_index(
        "ix_assistant_conversations_session_updated",
        "assistant_conversations",
        ["session_id", "updated_at"],
    )

    op.create_table(
        "assistant_messages",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
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
    op.drop_index("ix_assistant_conversations_session_updated", table_name="assistant_conversations")
    op.drop_table("assistant_conversations")

    op.create_table(
        "assistant_conversations",
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
