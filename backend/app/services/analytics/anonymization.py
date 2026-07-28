"""Pseudonymize person fields before anything is persisted.

The Power BI export comes from a real corporate environment. Nothing
identifiable may reach the database, an evidence file or a demo screen, so the
substitution happens on the way in — not on the way out, where a dump, an error
log or a screenshot would still expose the original.

Deterministic: the same name always maps to the same pseudonym, which keeps
"work by assignee" and the filter cascade meaningful without keeping identity.

Known limitation, deliberately not solved here: this is pseudonymization, not
strong anonymity. Whoever holds the original file can reverse it by comparison,
and free-text fields (assunto, detalhes, summary) may still carry a name typed
by a human. Adequate for a local demo base; not for publication.
"""
from __future__ import annotations

from hashlib import blake2b

# Person-carrying columns per table, by table name.
PERSON_COLUMNS: dict[str, tuple[str, ...]] = {
    "chamados_abertos": ("solicitante", "agente_tecnico"),
    "chamados_fechados": ("solicitante", "agente_tecnico"),
    "jira_cards": ("reporter", "reporter_id", "assignee", "assignee_id"),
}


def pseudonym(value: str | None, prefix: str = "P") -> str | None:
    """Return a stable pseudonym for a person value. ``None`` stays ``None``.

    An empty or whitespace-only value is absence, not a person.
    """
    if value is None:
        return None
    stripped = str(value).strip()
    if not stripped:
        return None
    digest = blake2b(stripped.casefold().encode("utf-8"), digest_size=5).hexdigest()
    return f"{prefix}-{digest}"


def anonymize_row(row: dict, table_name: str) -> dict:
    """Replace every person column of ``row`` in place-safe fashion.

    Returns the same dict so it can be used inline in a comprehension.
    """
    for column in PERSON_COLUMNS.get(table_name, ()):
        if column in row:
            row[column] = pseudonym(row[column])
    return row


def anonymize_rows(rows: list[dict], table_name: str) -> list[dict]:
    return [anonymize_row(row, table_name) for row in rows]


def is_covered(table_name: str) -> bool:
    """Whether this table has person columns declared at all.

    The ``anonymized`` column is written from this, never from a hardcoded
    ``True``: a table whose person columns were never declared must not claim
    to have been anonymized. Otherwise the audit column always approves itself
    and detects nothing — including the case it exists for, a new person column
    added without being registered in ``PERSON_COLUMNS``.
    """
    return bool(PERSON_COLUMNS.get(table_name))


def demo() -> None:
    """Self-check — this guards a privacy rule, so it gets a runnable one."""
    assert pseudonym("Maria Silva") == pseudonym("maria silva"), "must be case-insensitive"
    assert pseudonym("Maria Silva") == pseudonym("  Maria Silva  "), "must ignore padding"
    assert pseudonym("Maria Silva") != pseudonym("Joao Souza")
    assert pseudonym(None) is None
    assert pseudonym("   ") is None
    assert "Maria" not in (pseudonym("Maria Silva") or "")

    row = {"solicitante": "Maria Silva", "agente_tecnico": "Joao Souza", "squad": "Squad4"}
    out = anonymize_row(dict(row), "chamados_abertos")
    assert out["solicitante"] != "Maria Silva"
    assert out["agente_tecnico"] != "Joao Souza"
    assert out["squad"] == "Squad4", "non-person columns must be untouched"
    print("anonymization.demo OK")


if __name__ == "__main__":
    demo()
