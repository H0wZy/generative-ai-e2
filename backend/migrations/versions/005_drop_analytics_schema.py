"""005_drop_analytics_schema

Reports (upload de CSV/Power BI) sai do disco por completo — nada mais
consome a base histórica depois que a tela e a navegação são removidas
(specs/003-unified-ops-refresh). A migration 003 permanece intocada como
snapshot histórico; esta é uma limpeza de mão única, não uma reversão de
schema (o código que sabia recriar `analytics.*` também foi apagado).

Revision ID: 005
Revises: 004
Create Date: 2026-07-30
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DROP SCHEMA IF EXISTS analytics CASCADE")


def downgrade() -> None:
    # Recriar o schema exigiria o DDL de `app/services/analytics/tables.py`,
    # que foi deletado junto com o resto do módulo — não há para onde voltar.
    # Consistente com o código também ter saído (Princípio V): esta é uma
    # limpeza de mão única, não uma migration reversível.
    pass
