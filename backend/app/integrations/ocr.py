"""Cliente de OCR local via Ollama (specs/013, US3).

Mesmo padrão de adapter de `app/integrations/llm.py`: ``Protocol`` + cliente
real (``OllamaOcrClient``) + fake determinístico (``FakeOcrClient``) para
teste sem rede. Local por padrão — API paga de OCR exigiria ADR (constituição
IV), sem credencial nova.
"""
from __future__ import annotations

import base64
from dataclasses import dataclass, field
from typing import Protocol

import httpx

from app.core.config import Settings


class OcrClientError(Exception):
    """Falha de OCR — conexão, timeout, resposta inválida.

    Mensagem sempre estática: nunca inclui o conteúdo do arquivo (constituição
    IV), mesma regra de ``LLMClientError``.
    """


class OcrClientProtocol(Protocol):
    def extract_text(self, image_bytes: bytes) -> str: ...


class OllamaOcrClient:
    """Real adapter — chama o modelo de OCR local via ``/api/generate``.

    ``image_bytes`` precisa ser uma imagem já rasterizada (JPEG/PNG) — o
    campo ``images`` da API multimodal do Ollama espera um arquivo de
    imagem, não o PDF inteiro. O chamador (``routes_assistant.py``) extrai
    essa imagem da primeira página via
    ``pdf_extract.extract_first_page_image`` antes de chegar aqui.
    """

    def __init__(self, settings: Settings) -> None:
        self._base_url = settings.ocr_base_url.rstrip("/")
        self._model = settings.ocr_model

    def extract_text(self, image_bytes: bytes) -> str:
        try:
            with httpx.Client(timeout=120) as client:
                response = client.post(
                    f"{self._base_url}/api/generate",
                    json={
                        "model": self._model,
                        "prompt": "Extraia todo o texto legível desta imagem.",
                        "images": [base64.b64encode(image_bytes).decode("ascii")],
                        "stream": False,
                    },
                )
                response.raise_for_status()
                return response.json()["response"].strip()
        except httpx.HTTPError:
            raise OcrClientError("ocr request failed") from None
        except (KeyError, ValueError):
            raise OcrClientError("ocr returned an invalid response") from None


@dataclass
class FakeOcrClient:
    """Fake determinístico — sem rede. ``text`` simula o resultado do OCR;
    ``error`` simula falha de extração (PDF ilegível para o modelo).
    """

    text: str = "Texto extraído via OCR simulado."
    error: OcrClientError | None = None
    calls: list[bytes] = field(default_factory=list)

    def extract_text(self, image_bytes: bytes) -> str:
        self.calls.append(image_bytes)
        if self.error is not None:
            raise self.error
        return self.text
