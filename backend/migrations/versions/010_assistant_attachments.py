"""010_assistant_attachments

Upload de documento no chat do assistente com TreeRAG. Duas tabelas:
- assistant_attachments: metadados do anexo por conversa (um por conversa).
- assistant_attachment_nodes: árvore hierárquica do documento (nós-folha +
  seções + raiz sintética), com embeddings para busca bidirecional.

Ambas com ON DELETE CASCADE a partir de assistant_conversations.id /
assistant_attachments.id.

Revision ID: 010
Revises: 009
Create Date: 2026-08-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision = "010"
down_revision = "009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "assistant_attachments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "conversation_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assistant_conversations.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("file_name", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("error_reason", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "assistant_attachment_nodes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "attachment_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assistant_attachments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "parent_id",
            UUID(as_uuid=True),
            sa.ForeignKey("assistant_attachment_nodes.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("node_type", sa.String(10), nullable=False),
        sa.Column("level", sa.Integer, nullable=False),
        sa.Column("heading_path", sa.Text, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", sa.LargeBinary, nullable=True),
        sa.Column("start_line", sa.Integer, nullable=True),
        sa.Column("end_line", sa.Integer, nullable=True),
    )

    op.create_index(
        "ix_assistant_attachment_nodes_attachment_type",
        "assistant_attachment_nodes",
        ["attachment_id", "node_type"],
    )


def downgrade() -> None:
    op.drop_index("ix_assistant_attachment_nodes_attachment_type", table_name="assistant_attachment_nodes")
    op.drop_table("assistant_attachment_nodes")
    op.drop_table("assistant_attachments")
