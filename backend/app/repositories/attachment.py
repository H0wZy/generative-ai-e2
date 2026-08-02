"""AssistantAttachmentRepository — persistência do anexo efêmero por conversa
e dos nós da árvore (specs/013).

Um anexo por conversa: `create_or_replace` apaga o anterior antes de inserir
o novo (research.md R6) — nunca reprocessa a mesma linha.
"""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.assistant import AttachmentStatus
from app.repositories.schema import AssistantAttachmentNodeRow, AssistantAttachmentRow
from app.services.attachment_tree import AttachmentNode


class AssistantAttachmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_or_replace(
        self,
        conversation_id: uuid.UUID,
        *,
        file_name: str,
        mime_type: str,
        size_bytes: int,
        status: AttachmentStatus,
        error_reason: str | None = None,
        content: str | None = None,
    ) -> AssistantAttachmentRow:
        existing = self.get_by_conversation(conversation_id)
        if existing is not None:
            self._session.delete(existing)
            self._session.flush()

        attachment = AssistantAttachmentRow(
            id=uuid.uuid4(),
            conversation_id=conversation_id,
            file_name=file_name,
            mime_type=mime_type,
            size_bytes=size_bytes,
            status=status,
            error_reason=error_reason,
            content=content,
        )
        self._session.add(attachment)
        self._session.commit()
        self._session.refresh(attachment)
        return attachment

    def bulk_insert_nodes(self, attachment_id: uuid.UUID, nodes: list[AttachmentNode]) -> None:
        self._session.add_all(
            AssistantAttachmentNodeRow(
                id=node.id,
                attachment_id=attachment_id,
                parent_id=node.parent_id,
                node_type=node.node_type,
                level=node.level,
                heading_path=node.heading_path,
                content=node.content,
                embedding=node.embedding,
                start_line=node.start_line,
                end_line=node.end_line,
            )
            for node in nodes
        )
        self._session.commit()

    def get_by_conversation(self, conversation_id: uuid.UUID) -> AssistantAttachmentRow | None:
        return self._session.execute(
            select(AssistantAttachmentRow).where(
                AssistantAttachmentRow.conversation_id == conversation_id
            )
        ).scalar_one_or_none()

    def get_nodes(self, attachment_id: uuid.UUID) -> list[AssistantAttachmentNodeRow]:
        return list(
            self._session.execute(
                select(AssistantAttachmentNodeRow).where(
                    AssistantAttachmentNodeRow.attachment_id == attachment_id
                )
            ).scalars().all()
        )

    def delete_by_conversation(self, conversation_id: uuid.UUID) -> bool:
        attachment = self.get_by_conversation(conversation_id)
        if attachment is None:
            return False
        self._session.delete(attachment)
        self._session.commit()
        return True
