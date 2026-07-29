"""In-process TTL cache for Jira reads (research.md R7). No dependency."""
from __future__ import annotations

import time
from typing import Any, Callable, Hashable

CacheKey = tuple[Any, ...]


class TTLCache:
    def __init__(self, ttl_seconds: int = 60, clock: Callable[[], float] = time.monotonic) -> None:
        self._ttl = ttl_seconds
        self._clock = clock
        self._store: dict[Hashable, tuple[float, Any]] = {}

    def get(self, key: CacheKey) -> Any | None:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if self._clock() >= expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: CacheKey, value: Any) -> None:
        # Varre o que expirou antes de inserir. Sem isso o dicionário só
        # encolhe quando a MESMA chave é lida de novo, e `offset` faz parte da
        # chave do backlog: um cliente variando o offset criaria entradas que
        # nunca mais são lidas. A API não tem autenticação — é caminho de
        # exaustão de memória, não hipótese.
        now = self._clock()
        for expired in [k for k, (exp, _) in self._store.items() if now >= exp]:
            del self._store[expired]
        self._store[key] = (now + self._ttl, value)

    def invalidate(self, key: CacheKey) -> None:
        self._store.pop(key, None)

    def invalidate_prefix(self, prefix: Any) -> None:
        for key in [k for k in self._store if k[0] == prefix]:
            del self._store[key]
