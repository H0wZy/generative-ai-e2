"""008_conversation_archived

Arquivar conversa — tira das listas ativas ("Favoritos"/"Recentes") sem
excluir. Coluna temporal em vez de booleana: custa o mesmo e já registra
quando a conversa foi arquivada (specs/007 FR-012).

Nulável e sem default: as linhas existentes viram ativas sozinhas, sem
backfill e sem travar a tabela.

Revision ID: 008
Revises: 007
Create Date: 2026-08-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "008"
down_revision = "007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistant_conversations",
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("assistant_conversations", "archived_at")
