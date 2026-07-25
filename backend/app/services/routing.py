"""Deterministic squad routing — no I/O, no database."""
from __future__ import annotations

from app.domain.models import RoutingDecision

RULE_VERSION = "routing-rules/v1"

CATEGORY_TO_SQUAD: dict[str, str] = {
    "access": "identity",
    "billing": "finance",
    "incident": "platform",
    "integration": "platform",
}


def route_ticket(category: str | None) -> RoutingDecision:
    """Return a RoutingDecision for the given category string.

    Falls back to ``needs_human_review=True`` for unknown / missing categories.
    """
    normalized = (category or "").strip().lower()
    squad_id = CATEGORY_TO_SQUAD.get(normalized)
    if squad_id:
        return RoutingDecision(
            squad_id=squad_id,
            rule_version=RULE_VERSION,
            confidence=1.0,
            needs_human_review=False,
        )
    return RoutingDecision(
        squad_id=None,
        rule_version=f"{RULE_VERSION}:no-match",
        confidence=0.0,
        needs_human_review=True,
    )
