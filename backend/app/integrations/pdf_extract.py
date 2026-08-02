"""Extração de texto embutido de PDF (specs/013, US3).

Sem rede — biblioteca leve (`pypdf`) só para a camada de texto já embutida
no arquivo. PDF escaneado (sem essa camada) não é uma falha aqui: retorna
string vazia, que é o sinal para o chamador acionar OCR (research.md R4).
"""
from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PdfExtractError(Exception):
    """Arquivo corrompido/ilegível — distinto de "sem texto embutido"
    (esse caso retorna string vazia, não levanta exceção).
    """


def extract_pdf_text(content: bytes) -> str:
    try:
        reader = PdfReader(io.BytesIO(content))
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    except (PdfReadError, ValueError):
        raise PdfExtractError("pdf ilegível ou corrompido") from None


def extract_first_page_image(content: bytes) -> bytes | None:
    """Bytes da primeira imagem embutida (JPEG/PNG) encontrada no PDF, ou
    ``None`` se não houver nenhuma.

    PDF escaneado é, na prática, uma imagem de página inteira embutida como
    XObject — é essa imagem (não o arquivo PDF inteiro) que um modelo de
    visão via Ollama espera em ``images`` (research.md R4 assumia enviar o
    PDF cru; correção: modelo de visão espera imagem rasterizada).
    """
    try:
        reader = PdfReader(io.BytesIO(content))
        for page in reader.pages:
            images = page.images
            if images:
                return images[0].data
    except (PdfReadError, ValueError):
        raise PdfExtractError("pdf ilegível ou corrompido") from None
    return None
