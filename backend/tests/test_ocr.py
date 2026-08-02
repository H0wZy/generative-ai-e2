"""Testes de app/integrations/ocr.py com FakeOcrClient (specs/013, T026)."""
from __future__ import annotations

import pytest

from app.integrations.ocr import FakeOcrClient, OcrClientError


def test_fake_ocr_client_returns_configured_text() -> None:
    client = FakeOcrClient(text="conteúdo extraído do PDF escaneado")

    result = client.extract_text(b"%PDF-fake-bytes")

    assert result == "conteúdo extraído do PDF escaneado"
    assert client.calls == [b"%PDF-fake-bytes"]


def test_fake_ocr_client_raises_typed_error_without_leaking_content() -> None:
    client = FakeOcrClient(error=OcrClientError("ocr request failed"))

    with pytest.raises(OcrClientError) as excinfo:
        client.extract_text(b"conteudo sigiloso do arquivo")

    assert "conteudo sigiloso" not in str(excinfo.value)
