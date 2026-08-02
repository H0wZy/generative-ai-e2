"""Testes de contrato das 3 rotas de anexo (specs/013, T016/T028).

`.md`/`.txt` (US1) e `.pdf` (US3, texto embutido / OCR / ilegível).
"""
from __future__ import annotations

import io
import uuid

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.api.routes_assistant import create_assistant_router
from app.core.config import Settings
from app.integrations.ocr import FakeOcrClient, OcrClientError
from app.integrations.openrouter import FakeAssistantClient
from app.integrations.rag_search import FakeRagSearchClient

_SESSION_ID = "33333333-3333-3333-3333-333333333333"


def _settings() -> Settings:
    return Settings(database_url="postgresql://u:p@localhost:5432/db")  # type: ignore[arg-type]


def _client(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
    ocr_client: FakeOcrClient | None = None,
) -> TestClient:
    app = FastAPI()
    router = create_assistant_router(_settings(), session_factory)
    app.include_router(router)
    app.dependency_overrides[router.get_rag_client] = lambda: fake_rag
    app.dependency_overrides[router.get_model_client] = lambda: fake_assistant
    app.dependency_overrides[router.get_ocr_client] = lambda: ocr_client or FakeOcrClient()
    return TestClient(app)


def _create_conversation(client: TestClient) -> str:
    response = client.post("/api/v1/assistant/conversations", headers={"X-Session-Id": _SESSION_ID})
    assert response.status_code == 201
    return response.json()["id"]


def _pdf_with_embedded_text(text: str) -> bytes:
    content = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    objects = [
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj",
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj",
        b"3 0 obj<< /Type /Page /Parent 2 0 R /Resources << /Font << /F1 4 0 R >> >> "
        b"/MediaBox [0 0 612 792] /Contents 5 0 R >>endobj",
        b"4 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj",
        b"5 0 obj<< /Length " + str(len(content)).encode() + b" >>stream\n" + content + b"\nendstream endobj",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj + b"\n"
    xref_offset = len(pdf)
    pdf += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        pdf += ("%010d 00000 n \n" % off).encode()
    pdf += b"trailer<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\n"
    pdf += b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF"
    return pdf


def _pdf_without_embedded_text_or_image() -> bytes:
    """PDF válido, sem texto e sem imagem embutida — nem OCR tem o que ler."""
    objects = [
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj",
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj",
        b"3 0 obj<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 200 200] >>endobj",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj + b"\n"
    xref_offset = len(pdf)
    pdf += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        pdf += ("%010d 00000 n \n" % off).encode()
    pdf += b"trailer<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\n"
    pdf += b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF"
    return pdf


def _pdf_scanned_with_embedded_image() -> bytes:
    """PDF sem texto selecionável, com uma imagem de página inteira embutida
    (JPEG) — é como um PDF escaneado real se parece (research.md R4).
    """
    from PIL import Image

    img = Image.new("RGB", (20, 20), color=(120, 60, 30))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    jpeg_bytes = buf.getvalue()

    content_stream = b"q 20 0 0 20 0 0 cm /Im0 Do Q"
    objects = [
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj",
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj",
        b"3 0 obj<< /Type /Page /Parent 2 0 R /Resources << /XObject << /Im0 5 0 R >> >> "
        b"/MediaBox [0 0 20 20] /Contents 4 0 R >>endobj",
        b"4 0 obj<< /Length " + str(len(content_stream)).encode() + b" >>stream\n"
        + content_stream + b"\nendstream endobj",
        b"5 0 obj<< /Type /XObject /Subtype /Image /Width 20 /Height 20 /ColorSpace /DeviceRGB "
        b"/BitsPerComponent 8 /Filter /DCTDecode /Length " + str(len(jpeg_bytes)).encode() + b" >>stream\n"
        + jpeg_bytes + b"\nendstream endobj",
    ]
    pdf = b"%PDF-1.4\n"
    offsets = []
    for obj in objects:
        offsets.append(len(pdf))
        pdf += obj + b"\n"
    xref_offset = len(pdf)
    pdf += b"xref\n0 " + str(len(objects) + 1).encode() + b"\n0000000000 65535 f \n"
    for off in offsets:
        pdf += ("%010d 00000 n \n" % off).encode()
    pdf += b"trailer<< /Size " + str(len(objects) + 1).encode() + b" /Root 1 0 R >>\n"
    pdf += b"startxref\n" + str(xref_offset).encode() + b"\n%%EOF"
    return pdf


def test_upload_valid_markdown_is_ready(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)

    response = client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("manual.md", b"# Titulo\n\nConteudo do manual.", "text/markdown")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "ready"
    assert body["file_name"] == "manual.md"
    assert body["error_reason"] is None


def test_upload_unsupported_extension_is_rejected(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)

    response = client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("planilha.docx", b"conteudo qualquer", "application/octet-stream")},
    )

    assert response.status_code == 422


def test_upload_above_size_limit_is_rejected(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)

    huge = b"a" * (6_000_000)  # acima de attachment_max_bytes_text default (5 MB)
    response = client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("grande.txt", huge, "text/plain")},
    )

    assert response.status_code == 413


def test_upload_without_owning_conversation_is_404(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.post(
        f"/api/v1/assistant/conversations/{uuid.uuid4()}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("manual.md", b"# Titulo\n\nConteudo.", "text/markdown")},
    )

    assert response.status_code == 404


def test_get_attachment_without_upload_is_null(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)

    response = client.get(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
    )

    assert response.status_code == 200
    assert response.json() == {"attachment": None}


def test_get_attachment_after_upload_reflects_it(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)
    client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("manual.md", b"# Titulo\n\nConteudo.", "text/markdown")},
    )

    response = client.get(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
    )

    assert response.json()["attachment"]["file_name"] == "manual.md"


def test_get_attachment_content_after_upload_returns_full_text(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)
    body = b"# Titulo\n\nConteudo completo do documento para visualizacao."
    client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("manual.md", body, "text/markdown")},
    )

    response = client.get(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment/content",
        headers={"X-Session-Id": _SESSION_ID},
    )

    assert response.status_code == 200
    assert response.json() == {"file_name": "manual.md", "content": body.decode()}


def test_get_attachment_content_without_upload_is_404(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)

    response = client.get(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment/content",
        headers={"X-Session-Id": _SESSION_ID},
    )

    assert response.status_code == 404


def test_get_attachment_content_when_failed_is_404(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)
    client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("relatorio.txt", "".encode(), "text/plain")},
    )

    response = client.get(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment/content",
        headers={"X-Session-Id": _SESSION_ID},
    )

    assert response.status_code == 404


def test_get_attachment_content_without_owning_conversation_is_404(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)

    response = client.get(
        f"/api/v1/assistant/conversations/{uuid.uuid4()}/attachment/content",
        headers={"X-Session-Id": _SESSION_ID},
    )

    assert response.status_code == 404


def test_delete_attachment_is_idempotent(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)

    first = client.delete(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
    )
    assert first.status_code == 204

    client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("manual.md", b"# Titulo\n\nConteudo.", "text/markdown")},
    )
    second = client.delete(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
    )
    assert second.status_code == 204

    get_response = client.get(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
    )
    assert get_response.json() == {"attachment": None}


def test_upload_replaces_previous_attachment(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    """research.md R6 — novo upload substitui o anterior como fonte ativa."""
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)

    client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("primeiro.md", b"# A\n\nConteudo A.", "text/markdown")},
    )
    client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("segundo.md", b"# B\n\nConteudo B.", "text/markdown")},
    )

    response = client.get(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
    )
    assert response.json()["attachment"]["file_name"] == "segundo.md"


def test_upload_pdf_with_embedded_text_is_ready_via_pdf_extract(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)

    response = client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("manual.pdf", _pdf_with_embedded_text("Manual do Sistema"), "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "ready"


def test_upload_scanned_pdf_without_embedded_text_falls_back_to_ocr(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    ocr_client = FakeOcrClient(text="Texto reconhecido via OCR do PDF escaneado.")
    client = _client(session_factory, fake_rag, fake_assistant, ocr_client=ocr_client)
    conversation_id = _create_conversation(client)

    response = client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("escaneado.pdf", _pdf_scanned_with_embedded_image(), "application/pdf")},
    )

    assert response.status_code == 201
    assert response.json()["status"] == "ready"
    assert ocr_client.calls, "esperava que o OCR fosse acionado por falta de texto embutido"
    # OCR recebe a imagem rasterizada da página, não o PDF inteiro (correção
    # sobre o design original de research.md R4 — modelo de visão do Ollama
    # espera JPEG/PNG em `images`, não o arquivo PDF cru em base64).
    assert ocr_client.calls[0].startswith(b"\xff\xd8"), "esperava bytes de JPEG, não o PDF inteiro"


def test_upload_pdf_when_ocr_fails_marks_failed_with_reason(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    ocr_client = FakeOcrClient(error=OcrClientError("ocr request failed"))
    client = _client(session_factory, fake_rag, fake_assistant, ocr_client=ocr_client)
    conversation_id = _create_conversation(client)

    response = client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("escaneado.pdf", _pdf_scanned_with_embedded_image(), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_reason"]


def test_upload_pdf_without_text_or_image_marks_failed_without_calling_ocr(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    """Nem texto embutido, nem imagem para o OCR ler — falha sem chamar OCR."""
    ocr_client = FakeOcrClient()
    client = _client(session_factory, fake_rag, fake_assistant, ocr_client=ocr_client)
    conversation_id = _create_conversation(client)

    response = client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("vazio.pdf", _pdf_without_embedded_text_or_image(), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_reason"]
    assert ocr_client.calls == []


def test_upload_pdf_corrupted_marks_failed_without_error_http_status(
    session_factory: sessionmaker[Session],
    fake_rag: FakeRagSearchClient,
    fake_assistant: FakeAssistantClient,
) -> None:
    client = _client(session_factory, fake_rag, fake_assistant)
    conversation_id = _create_conversation(client)

    response = client.post(
        f"/api/v1/assistant/conversations/{conversation_id}/attachment",
        headers={"X-Session-Id": _SESSION_ID},
        files={"file": ("quebrado.pdf", b"%PDF-1.4\nnao e um pdf de verdade", "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "failed"
    assert body["error_reason"]
