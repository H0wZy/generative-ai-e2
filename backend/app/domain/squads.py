"""Closed squad enum — the real squads, taken from the Freshservice export.

Replaces the synthetic ``identity``/``finance``/``platform`` set. The squad is
already a filled-in field on the Freshservice ticket, so routing reads it
instead of inferring it from the category.
"""
from __future__ import annotations

import unicodedata

# Canonical spelling. Order is the order they appear in the historical export.
SQUADS: tuple[str, ...] = (
    "Squad1",
    "Squad2",
    "Squad4",
    "Squad5",
    "Squad6",
    "Squad8",
    "Datastage",
    "Fresh",
    "GCP",
    "RPA",
    "STD",
    "VSSPS",
    "WordPress",
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
