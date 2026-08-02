"""Testes de AssistantAttachmentRepository (specs/013).

Cobre create_or_replace/get/delete e o edge case de cascade ao excluir a
conversa (quickstart.md Roteiro 6, T031).
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.repositories.assistant import AssistantConversationRepository
from app.repositories.attachment import AssistantAttachmentRepository
from app.repositories.schema import AssistantAttachmentNodeRow, AssistantAttachmentRow
from app.services.attachment_tree import build_tree

_SESSION_ID = uuid.uuid4()


def _new_conversation(session_factory: sessionmaker[Session]) -> uuid.UUID:
    session = session_factory()
    conversation = AssistantConversationRepository(session).create_conversation(_SESSION_ID)
    conversation_id = conversation.id
    session.close()
    return conversation_id


def test_create_or_replace_persists_attachment_and_nodes(session_factory: sessionmaker[Session]) -> None:
    conversation_id = _new_conversation(session_factory)
    session = session_factory()
    repo = AssistantAttachmentRepository(session)

    attachment = repo.create_or_replace(
        conversation_id,
        file_name="manual.md",
        mime_type="text/markdown",
        size_bytes=42,
        status="ready",
    )
    nodes = build_tree("# Título\n\nConteúdo do documento.")
    repo.bulk_insert_nodes(attachment.id, nodes)

    fetched = repo.get_by_conversation(conversation_id)
    assert fetched is not None
    assert fetched.file_name == "manual.md"
    assert len(repo.get_nodes(attachment.id)) == len(nodes)
    session.close()


def test_create_or_replace_replaces_previous_attachment(session_factory: sessionmaker[Session]) -> None:
    conversation_id = _new_conversation(session_factory)
    session = session_factory()
    repo = AssistantAttachmentRepository(session)

    first = repo.create_or_replace(
        conversation_id, file_name="a.md", mime_type="text/markdown", size_bytes=1, status="ready"
    )
    repo.bulk_insert_nodes(first.id, build_tree("# A\n\nconteúdo A"))

    second = repo.create_or_replace(
        conversation_id, file_name="b.md", mime_type="text/markdown", size_bytes=1, status="ready"
    )
    repo.bulk_insert_nodes(second.id, build_tree("# B\n\nconteúdo B"))

    fetched = repo.get_by_conversation(conversation_id)
    assert fetched is not None
    assert fetched.file_name == "b.md"
    assert (
        session.execute(
            select(AssistantAttachmentRow).where(AssistantAttachmentRow.id == first.id)
        ).scalar_one_or_none()
        is None
    )
    assert (
        session.execute(
            select(AssistantAttachmentNodeRow).where(AssistantAttachmentNodeRow.attachment_id == first.id)
        ).scalar_one_or_none()
        is None
    )
    session.close()


def test_delete_by_conversation_is_idempotent(session_factory: sessionmaker[Session]) -> None:
    conversation_id = _new_conversation(session_factory)
    session = session_factory()
    repo = AssistantAttachmentRepository(session)

    assert repo.delete_by_conversation(conversation_id) is False

    attachment = repo.create_or_replace(
        conversation_id, file_name="a.md", mime_type="text/markdown", size_bytes=1, status="ready"
    )
    repo.bulk_insert_nodes(attachment.id, build_tree("# A\n\nconteúdo"))

    assert repo.delete_by_conversation(conversation_id) is True
    assert repo.get_by_conversation(conversation_id) is None
    session.close()


def test_deleting_conversation_cascades_attachment_and_nodes(session_factory: sessionmaker[Session]) -> None:
    """quickstart.md Roteiro 6 — excluir a conversa some com o anexo e nós junto."""
    conversation_id = _new_conversation(session_factory)
    session = session_factory()
    attachment = AssistantAttachmentRepository(session).create_or_replace(
        conversation_id, file_name="a.md", mime_type="text/markdown", size_bytes=1, status="ready"
    )
    AssistantAttachmentRepository(session).bulk_insert_nodes(attachment.id, build_tree("# A\n\nconteúdo"))
    attachment_id = attachment.id
    session.close()

    session = session_factory()
    AssistantConversationRepository(session).delete_conversation(conversation_id, _SESSION_ID)
    session.close()

    session = session_factory()
    assert (
        session.execute(
            select(AssistantAttachmentRow).where(AssistantAttachmentRow.id == attachment_id)
        ).scalar_one_or_none()
        is None
    )
    assert (
        session.execute(
            select(AssistantAttachmentNodeRow).where(AssistantAttachmentNodeRow.attachment_id == attachment_id)
        ).scalar_one_or_none()
        is None
    )
    session.close()
