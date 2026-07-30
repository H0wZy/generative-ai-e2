"""Offline eval: LLM squad classification against tests/golden/routing_golden.jsonl.

Requires the OpenRouter provider configured (`OPENROUTER_API_KEY`). Never
runs as part of ``make test`` — it hits the real model, so results vary run
to run. Prints accuracy, abstention rate and the list of wrong classifications.

Prompt-injection resistance is a probabilistic property of the real model —
it can only be measured against it, never against ``FakeLLMClient``. Cases
with ``kind: "injection"`` are reported separately, as a measured attack
success rate, not folded into the general accuracy number.

Usage: python -m scripts.routing_eval
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import get_settings
from app.integrations.llm import LLMClientError, OpenRouterSquadClient, resolve_squad

GOLDEN_PATH = Path(__file__).resolve().parent.parent / "tests" / "golden" / "routing_golden.jsonl"


@dataclass
class GoldenCase:
    id: str
    subject: str
    description: str
    expected_squad: str | None
    kind: str | None = None
    note: str | None = None


def load_golden(path: Path = GOLDEN_PATH) -> list[GoldenCase]:
    cases = []
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        raw = json.loads(line)
        cases.append(GoldenCase(**raw))
    return cases


def _classify(
    client: OpenRouterSquadClient, case: GoldenCase, threshold: float
) -> tuple[str | None, bool, str | None]:
    """Returns (squad_id, needs_human_review, error_message)."""
    try:
        result = client.classify_squad(case.subject, case.description)
    except LLMClientError as exc:
        return None, True, str(exc)
    squad_id, needs_human_review = resolve_squad(result, threshold)
    return squad_id, needs_human_review, None


def main() -> None:
    settings = get_settings()
    client = OpenRouterSquadClient(settings)
    cases = load_golden()
    threshold = settings.llm_confidence_threshold

    scored_cases = [c for c in cases if c.kind != "injection"]
    injection_cases = [c for c in cases if c.kind == "injection"]

    total_with_expected = 0
    correct = 0
    abstained = 0
    errors: list[str] = []

    for case in scored_cases:
        squad_id, needs_human_review, err = _classify(client, case, threshold)
        if err is not None:
            errors.append(f"{case.id}: llm error ({err})")
        if needs_human_review:
            abstained += 1

        if case.expected_squad is not None:
            total_with_expected += 1
            if squad_id == case.expected_squad:
                correct += 1
            else:
                errors.append(
                    f"{case.id}: expected={case.expected_squad!r} got={squad_id!r} "
                    f"needs_human_review={needs_human_review}"
                )
        elif not needs_human_review:
            errors.append(f"{case.id}: expected abstention, got confident squad={squad_id!r}")

    accuracy = correct / total_with_expected if total_with_expected else 0.0
    abstention_rate = abstained / len(scored_cases) if scored_cases else 0.0

    print(f"model={settings.llm_model} threshold={threshold}")
    print(f"cases={len(scored_cases)} with_expected_squad={total_with_expected}")
    print(f"accuracy={accuracy:.2%} ({correct}/{total_with_expected})")
    print(f"abstention_rate={abstention_rate:.2%} ({abstained}/{len(scored_cases)})")
    if errors:
        print(f"errors ({len(errors)}):")
        for err in errors:
            print(f"  - {err}")
    else:
        print("errors: none")

    # ------------------------------------------------------------------
    # Injection cases — measured attack success rate against the real
    # model. Not a pass/fail gate: a probabilistic number, reported as-is.
    # ------------------------------------------------------------------
    print()
    print(f"injection_cases={len(injection_cases)}")
    attack_successes = []
    for case in injection_cases:
        squad_id, needs_human_review, err = _classify(client, case, threshold)
        if not needs_human_review:
            attack_successes.append(f"{case.id}: model returned confident squad={squad_id!r} (attack succeeded)")
        elif err is not None:
            attack_successes.append(f"{case.id}: llm error, counted as abstention ({err})")

    if injection_cases:
        rate = len([s for s in attack_successes if "attack succeeded" in s]) / len(injection_cases)
        print(f"injection_attack_success_rate={rate:.2%}")
    for line in attack_successes:
        print(f"  - {line}")


if __name__ == "__main__":
    main()
