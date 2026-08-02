"""011_assistant_attachment_content

Guarda o texto extraído do anexo (pré-chunking) em `assistant_attachments`
para permitir visualizar o documento inteiro depois do upload — os nós da
árvore não servem pra isso: raiz/seções têm conteúdo truncado (só material
de embedding) e folhas podem se sobrepor quando o chunker divide um trecho
grande demais em janelas com overlap.

Revision ID: 011
Revises: 010
Create Date: 2026-08-02
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "011"
down_revision = "010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("assistant_attachments", sa.Column("content", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("assistant_attachments", "content")
