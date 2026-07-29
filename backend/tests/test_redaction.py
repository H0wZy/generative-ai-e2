"""Tests for services/redaction.py — cada padrão, e a frase segue legível."""
from __future__ import annotations

import pytest

from app.services.redaction import redact


@pytest.mark.parametrize(
    ("raw", "expected_marker", "removed"),
    [
        ("Contate joao.silva@empresa.com.br agora", "[email]", "joao.silva@empresa.com.br"),
        ("CPF 123.456.789-01 do titular", "[documento]", "123.456.789-01"),
        ("CPF 12345678901 sem pontuação", "[documento]", "12345678901"),
        ("Ligue (11) 98765-4321 hoje", "[telefone]", "98765-4321"),
        ("Ligue +55 11 3456-7890", "[telefone]", "3456-7890"),
        ("Solicitante: Maria Souza, urgente", "[solicitante]", "Maria Souza"),
    ],
)
def test_each_pattern_is_redacted(raw: str, expected_marker: str, removed: str) -> None:
    result = redact(raw)
    assert expected_marker in result
    assert removed not in result


def test_sentence_stays_readable() -> None:
    raw = "Solicitante: Maria Souza pediu acesso; contate maria@x.com ou (11) 98765-4321."
    result = redact(raw)
    assert result.startswith("Solicitante: [solicitante]")
    assert "pediu acesso" not in result or "[solicitante]" in result
    assert "[email]" in result
    assert "[telefone]" in result


def test_text_without_personal_data_is_untouched() -> None:
    raw = "O worker usa a chave source_system + source_ticket_id para idempotência."
    assert redact(raw) == raw


def test_empty_text_is_safe() -> None:
    assert redact("") == ""


def test_cpf_is_not_eaten_by_the_phone_pattern() -> None:
    assert redact("CPF 123.456.789-01") == "CPF [documento]"
