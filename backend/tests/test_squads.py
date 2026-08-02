"""normalize_squad nunca devolve valor fora do conjunto canônico.

specs/012 — squads legadas (platform/identity/finance/Squad4) precisam
degradar para None (revisão humana / LLM), nunca virar squad_id gravado
cru. Cobre o caminho ao vivo; o backfill de dado histórico já gravado é
tratado pela migration 009, sem infraestrutura de teste de migration no
projeto (suíte usa Base.metadata.create_all, não Alembic).
"""
from __future__ import annotations

import pytest

from app.domain.squads import SQUADS, is_known_squad, normalize_squad


@pytest.mark.parametrize("raw", ["SQUAD-01", "squad-01", "SQUAD01"])
def test_normalize_squad_accepts_canonical_variants(raw: str) -> None:
    assert normalize_squad(raw) == "SQUAD-01"


@pytest.mark.parametrize("legacy", ["platform", "identity", "finance", "Squad4", "PLATFORM"])
def test_normalize_squad_rejects_legacy_names(legacy: str) -> None:
    # Nomes legados não são sinônimo de nenhum squad canônico — precisam
    # cair em None (revisão humana/LLM), nunca virar squad_id gravado cru.
    assert normalize_squad(legacy) is None


def test_normalize_squad_rejects_none_and_empty() -> None:
    assert normalize_squad(None) is None
    assert normalize_squad("") is None


def test_is_known_squad_matches_normalize_squad() -> None:
    assert is_known_squad("SQUAD-08") is True
    assert is_known_squad("platform") is False


def test_squads_tuple_is_all_canonical() -> None:
    assert SQUADS == tuple(f"SQUAD-{n:02d}" for n in range(1, 9))
