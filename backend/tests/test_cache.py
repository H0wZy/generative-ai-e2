"""Tests for the in-process TTL cache (services/cache.py)."""
from __future__ import annotations

from app.services.cache import TTLCache


def test_set_sweeps_expired_entries_so_the_store_stays_bounded():
    """Chave carrega `offset`, que vem do cliente: sem varredura o dicionário
    só encolhe quando a MESMA chave é relida, e nunca é."""
    now = [0.0]
    cache = TTLCache(ttl_seconds=60, clock=lambda: now[0])

    for offset in range(50):
        cache.set(("backlog", 2, 100, offset), {"data": offset})
    assert len(cache._store) == 50

    now[0] = 61.0
    cache.set(("backlog", 2, 100, 999), {"data": 999})
    assert len(cache._store) == 1


def test_hit_within_ttl() -> None:
    now = [0.0]
    cache = TTLCache(ttl_seconds=60, clock=lambda: now[0])

    cache.set(("workflows", None, "status=failed"), {"total": 1})
    now[0] = 59.0

    assert cache.get(("workflows", None, "status=failed")) == {"total": 1}


def test_miss_after_expiry() -> None:
    now = [0.0]
    cache = TTLCache(ttl_seconds=60, clock=lambda: now[0])

    cache.set(("agile/sprint", 2, ""), {"sprint": "x"})
    now[0] = 60.0

    assert cache.get(("agile/sprint", 2, "")) is None


def test_invalidate_clears_key() -> None:
    now = [0.0]
    cache = TTLCache(ttl_seconds=60, clock=lambda: now[0])

    cache.set(("agile/board", 2, "scope=sprint"), {"columns": []})
    cache.invalidate(("agile/board", 2, "scope=sprint"))

    assert cache.get(("agile/board", 2, "scope=sprint")) is None


def test_invalidate_prefix_clears_matching_keys() -> None:
    now = [0.0]
    cache = TTLCache(ttl_seconds=60, clock=lambda: now[0])

    cache.set(("agile/board", 2, "scope=sprint"), {"columns": []})
    cache.set(("agile/sprint", 2, ""), {"sprint": "x"})
    cache.invalidate_prefix("agile/board")

    assert cache.get(("agile/board", 2, "scope=sprint")) is None
    assert cache.get(("agile/sprint", 2, "")) == {"sprint": "x"}
