"""007_conversation_favorite

Favoritar/fixar conversa — sobe pra uma seção separada na sidebar, acima de
"Recentes" (igual "pin" de outros clientes de chat). Coluna nova, sem dado
de produção a migrar (era tudo False).

Revision ID: 007
Revises: 006
Create Date: 2026-07-31
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "007"
down_revision = "006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "assistant_conversations",
        sa.Column("is_favorite", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("assistant_conversations", "is_favorite")
