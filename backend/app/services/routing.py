"""Deterministic squad routing — no I/O, no database.

The squad is a field the Freshservice ticket already carries, so routing reads
it instead of guessing from the category. A value outside the closed enum is
the same case as a missing one: deterministic routing cannot decide, and the
item goes to the LLM fallback or to human review.
"""
from __future__ import annotations

from app.domain.models import RoutingDecision
from app.domain.squads import normalize_squad

RULE_VERSION = "routing-rules/v2"


def route_ticket(squad: str | None) -> RoutingDecision:
    """Return a RoutingDecision for the squad reported by the source ticket.

    Falls back to ``needs_human_review=True`` when the squad is missing or is
    not one of the known squads.
    """
    squad_id = normalize_squad(squad)
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
