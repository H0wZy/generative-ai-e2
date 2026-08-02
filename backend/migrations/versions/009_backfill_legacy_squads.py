"""009_backfill_legacy_squads

Squads legadas (`platform`, `identity`, `finance`, `Squad4` sem formatação)
gravadas em `workflow_executions.squad_id` antes da canonicalização em
`app/domain/squads.py` (SQUAD-01..SQUAD-08) ainda apareciam cruas na UI —
specs/012. Mapeamento arbitrário 1:1 entre os 4 nomes legados observados e
os 4 primeiros squads canônicos (não há informação de negócio que amarre
"platform" a um squad específico; squads.py já documenta que os squads são
genéricos, não a organização real do cliente).

`routing_decisions.squad_id` NÃO é tocado por esta migration: é o registro
de auditoria imutável da decisão tomada naquele momento (Constituição
§III, rastreabilidade) — reescrever retroativamente falsificaria o que foi
de fato decidido sob a nomenclatura antiga. Só o campo de estado atual
(`workflow_executions.squad_id`, usado para exibição e filtro) é corrigido.

Revision ID: 009
Revises: 008
Create Date: 2026-08-02
"""

from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "009"
down_revision = "008"
branch_labels = None
depends_on = None

_LEGACY_TO_CANONICAL = {
    "platform": "SQUAD-01",
    "identity": "SQUAD-02",
    "finance": "SQUAD-03",
    "Squad4": "SQUAD-04",
}


def upgrade() -> None:
    for legacy, canonical in _LEGACY_TO_CANONICAL.items():
        op.execute(
            "UPDATE workflow_executions SET squad_id = '%s' WHERE squad_id = '%s'"
            % (canonical, legacy)
        )


def downgrade() -> None:
    # Não há como distinguir, entre as linhas hoje em SQUAD-01..SQUAD-04,
    # quais vieram do backfill e quais já nasceram canônicas pelo
    # roteamento normal — reverter reescreveria dado correto. Mão única,
    # mesmo padrão de 005_drop_analytics_schema.py.
    pass
