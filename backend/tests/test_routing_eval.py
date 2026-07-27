"""Parsing check for the golden set loader — no Ollama, no DB."""
from __future__ import annotations

from scripts.routing_eval import load_golden


def test_golden_set_has_minimum_cases_and_injection_kind() -> None:
    cases = load_golden()
    assert len(cases) >= 15

    injection = [c for c in cases if c.kind == "injection"]
    abstention = [c for c in cases if c.expected_squad is None]

    assert len(injection) >= 2, "spec requires real prompt-injection cases (valid enum + high confidence)"
    assert len(abstention) >= 2

    # g16 must not be miscounted as a real injection test — it's enum closure.
    enum_case = next(c for c in cases if c.id == "g16")
    assert enum_case.kind == "enum_validation"
