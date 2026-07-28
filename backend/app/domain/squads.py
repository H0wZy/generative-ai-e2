"""Closed squad enum — generic placeholders, not the client's real org chart.

Replaces the synthetic ``identity``/``finance``/``platform`` set. The real
Freshservice tenant is not reachable (no API key released for this account,
and the client's org chart is out of scope to replicate), so the pipeline
runs against a mock with 8 generic squads instead. The squad is a filled-in
field on the ticket either way, so routing still just reads it instead of
inferring it from the category.
"""
from __future__ import annotations

import unicodedata

# Canonical spelling. Generic placeholders (SQUAD-01..SQUAD-08) — see module
# docstring for why these replace the client's real squad names.
SQUADS: tuple[str, ...] = (
    "SQUAD-01",
    "SQUAD-02",
    "SQUAD-03",
    "SQUAD-04",
    "SQUAD-05",
    "SQUAD-06",
    "SQUAD-07",
    "SQUAD-08",
)

# Lookup keyed by the normalized form, so "squad 4" and "SQUAD4" both resolve.
_BY_NORMALIZED: dict[str, str] = {}


def _normalize(value: str) -> str:
    """Strip accents, spaces, punctuation and case."""
    decomposed = unicodedata.normalize("NFKD", value)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    return "".join(c for c in without_accents if c.isalnum()).lower()


for _squad in SQUADS:
    _BY_NORMALIZED[_normalize(_squad)] = _squad


def normalize_squad(value: str | None) -> str | None:
    """Return the canonical squad name, or ``None`` when it is not a known squad.

    ``None`` is the answer for a missing field *and* for a value outside the
    enum — both mean "deterministic routing can't decide", which is exactly
    the case the LLM fallback exists for.
    """
    if not value:
        return None
    return _BY_NORMALIZED.get(_normalize(value))


def is_known_squad(value: str | None) -> bool:
    return normalize_squad(value) is not None
