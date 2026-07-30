"""AssistantConversationRepository — persistence for session-scoped chat history.

No business rules live here.  One transaction per public method (same house
style as ``workflows.py``).
"""
from __future__ import annotations

import uuid
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.repositories.schema import AssistantConversationRow, AssistantMessageRow


class AssistantConversationRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_or_create(self, session_id: uuid.UUID) -> AssistantConversationRow:
        """Return the conversation row for ``session_id``, creating it if absent."""
        conversation = self._session.get(AssistantConversationRow, session_id)
        if conversation is None:
            conversation = AssistantConversationRow(session_id=session_id)
            self._session.add(conversation)
            self._session.flush()  # get created_at server default applied
        return conversation

    def append_message(
        self,
        session_id: uuid.UUID,
        role: Literal["user", "assistant"],
        text: str,
        sources_json: str | None,
    ) -> None:
        """Insert one message. Creates the conversation first if it doesn't exist yet."""
        self.get_or_create(session_id)
        self._session.add(
            AssistantMessageRow(
                id=uuid.uuid4(),
                conversation_id=session_id,
                role=role,
                text=text,
                sources_json=sources_json,
            )
        )
        self._session.commit()

    def list_messages(self, session_id: uuid.UUID) -> list[AssistantMessageRow]:
        """All messages for the session, oldest first."""
        return list(
            self._session.execute(
                select(AssistantMessageRow)
                .where(AssistantMessageRow.conversation_id == session_id)
                .order_by(AssistantMessageRow.created_at)
            ).scalars().all()
        )
