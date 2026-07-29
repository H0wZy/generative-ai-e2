"""Redação de dado pessoal antes de o texto sair do processo (FR-040).

Função pura, sem estado e sem rede. O marcador é estável para que a frase
continue legível: "contate [email] no [telefone]" ainda diz o que aconteceu,
sem carregar o dado.

O modelo do assistente roda em provedor remoto de nível gratuito, que pode
reter prompt para treino. Aqui é o único ponto onde essa saída é filtrada.
"""
from __future__ import annotations

import re

# Ordem importa: CPF antes de telefone, senão a máscara de telefone come os
# 11 dígitos do CPF.
_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), "[email]"),
    (re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"), "[documento]"),
    (
        re.compile(r"(?<!\d)(?:\+55\s?)?(?:\(?\d{2}\)?[\s.-]?)?9?\d{4}[\s.-]?\d{4}(?!\d)"),
        "[telefone]",
    ),
)

_REQUESTER = re.compile(
    r"\b(solicitante|requester|reportado por|aberto por)\b\s*[:\-]?\s*[^\n,;.]{1,60}",
    re.IGNORECASE,
)


def redact(text: str) -> str:
    """Remove e-mail, documento, telefone e nome de solicitante."""
    if not text:
        return text

    redacted = text
    for pattern, marker in _PATTERNS:
        redacted = pattern.sub(marker, redacted)
    redacted = _REQUESTER.sub(lambda m: f"{m.group(1)}: [solicitante]", redacted)
    return redacted
