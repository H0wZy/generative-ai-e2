"""AssistantConversationRepository — persistence for named, per-session chat
conversations. Several conversations can belong to the same `session_id`.

No business rules live here. One transaction per public method (same house
style as ``workflows.py``).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.schema import AssistantConversationRow, AssistantMessageRow

_TITLE_MAX_CHARS = 48


class AssistantConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def create_conversation(self, session_id: uuid.UUID) -> AssistantConversationRow:
        """Sem título ainda — vira o começo da primeira pergunta (``append_message``)."""
        conversation = AssistantConversationRow(id=uuid.uuid4(), session_id=session_id)
        self._session.add(conversation)
        self._session.commit()
        self._session.refresh(conversation)
        return conversation

    def list_conversations(
        self, session_id: uuid.UUID, state: Literal["active", "archived"] = "active"
    ) -> list[AssistantConversationRow]:
        """Ativas: favoritadas primeiro, depois mais recentemente atualizada.

        Arquivadas: mais recentemente arquivada primeiro, ignorando favorita —
        é a ordem que se espera ao procurar o que acabou de sair da frente.

        Default `active` preserva o comportamento de quem já chamava isto.
        """
        query = select(AssistantConversationRow).where(
            AssistantConversationRow.session_id == session_id
        )
        if state == "archived":
            return list(
                self._session.execute(
                    query.where(AssistantConversationRow.archived_at.is_not(None)).order_by(
                        AssistantConversationRow.archived_at.desc()
                    )
                ).scalars().all()
            )
        return list(
            self._session.execute(
                query.where(AssistantConversationRow.archived_at.is_(None)).order_by(
                    AssistantConversationRow.is_favorite.desc(),
                    AssistantConversationRow.updated_at.desc(),
                )
            ).scalars().all()
        )

    def get_owned(
        self, conversation_id: uuid.UUID, session_id: uuid.UUID
    ) -> AssistantConversationRow | None:
        """Só devolve a conversa se pertencer a `session_id` — sem isso, uma sessão
        poderia ler o histórico de outra só adivinhando um UUID.
        """
        return self._session.execute(
            select(AssistantConversationRow).where(
                AssistantConversationRow.id == conversation_id,
                AssistantConversationRow.session_id == session_id,
            )
        ).scalar_one_or_none()

    def append_message(
        self,
        conversation_id: uuid.UUID,
        role: Literal["user", "assistant"],
        text: str,
        sources_json: str | None,
    ) -> None:
        """Best-effort: se a conversa não existe (ou foi apagada), não insere nada
        em vez de recriá-la — evita conversa órfã sem dono legítimo.
        """
        conversation = self._session.get(AssistantConversationRow, conversation_id)
        if conversation is None:
            return
        if not conversation.title and role == "user":
            conversation.title = (
                text
                if len(text) <= _TITLE_MAX_CHARS
                else text[:_TITLE_MAX_CHARS].rstrip() + "…"
            )
        conversation.updated_at = datetime.now(timezone.utc)
        self._session.add(
            AssistantMessageRow(
                id=uuid.uuid4(),
                conversation_id=conversation_id,
                role=role,
                text=text,
                sources_json=sources_json,
            )
        )
        self._session.commit()

    def rename_conversation(
        self, conversation_id: uuid.UUID, session_id: uuid.UUID, title: str
    ) -> bool:
        """`False` se a conversa não existe ou não pertence a `session_id`."""
        conversation = self.get_owned(conversation_id, session_id)
        if conversation is None:
            return False
        conversation.title = title
        self._session.commit()
        return True

    def set_favorite(
        self, conversation_id: uuid.UUID, session_id: uuid.UUID, is_favorite: bool
    ) -> bool:
        conversation = self.get_owned(conversation_id, session_id)
        if conversation is None:
            return False
        conversation.is_favorite = is_favorite
        self._session.commit()
        return True

    def set_archived(
        self, conversation_id: uuid.UUID, session_id: uuid.UUID, is_archived: bool
    ) -> bool:
        """O carimbo é do servidor, nunca do cliente — relógio de navegador não
        vira dado persistido.

        Arquivar duas vezes preserva o carimbo original: FR-012 registra quando
        a conversa foi arquivada, não quando o botão foi clicado por último.
        Não toca `updated_at` (que ordena "Recentes") nem `is_favorite`.
        """
        conversation = self.get_owned(conversation_id, session_id)
        if conversation is None:
            return False
        if not is_archived:
            conversation.archived_at = None
        elif conversation.archived_at is None:
            conversation.archived_at = datetime.now(timezone.utc)
        self._session.commit()
        return True

    def delete_conversation(self, conversation_id: uuid.UUID, session_id: uuid.UUID) -> bool:
        """Cascateia pra `assistant_messages` via FK ``ondelete=CASCADE``."""
        conversation = self.get_owned(conversation_id, session_id)
        if conversation is None:
            return False
        self._session.delete(conversation)
        self._session.commit()
        return True

    def list_messages(self, conversation_id: uuid.UUID) -> list[AssistantMessageRow]:
        """Todas as mensagens da conversa, mais antiga primeiro."""
        return list(
            self._session.execute(
                select(AssistantMessageRow)
                .where(AssistantMessageRow.conversation_id == conversation_id)
                .order_by(AssistantMessageRow.created_at)
            ).scalars().all()
        )
