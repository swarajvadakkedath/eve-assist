"""Session management for conversations."""

from datetime import datetime, timedelta, timezone
from typing import Any

from aios.conversation.models import Session
from aios.conversation.exceptions import SessionNotFoundError
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class SessionManager:
    def __init__(self, session_timeout_minutes: int = 30):
        self._sessions: dict[str, Session] = {}
        self._session_timeout = timedelta(minutes=session_timeout_minutes)

    async def create_session(self, conversation_id: str, context: dict | None = None) -> Session:
        session = Session(
            conversation_id=conversation_id,
            current_context=context or {},
            expires_at=datetime.now(timezone.utc) + self._session_timeout,
        )
        self._sessions[session.session_id] = session
        logger.info("session.created", session_id=session.session_id, conversation_id=conversation_id)
        return session

    async def get_session(self, session_id: str) -> Session | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        if session.expires_at and datetime.now(timezone.utc) > session.expires_at:
            self._sessions.pop(session_id, None)
            return None
        return session

    async def get_or_create_session(self, conversation_id: str, context: dict | None = None) -> Session:
        for session in self._sessions.values():
            if session.conversation_id == conversation_id:
                if session.expires_at and datetime.now(timezone.utc) > session.expires_at:
                    continue
                session.expires_at = datetime.now(timezone.utc) + self._session_timeout
                return session
        return await self.create_session(conversation_id, context)

    async def update_session_context(self, session_id: str, context: dict) -> Session:
        session = await self.get_session(session_id)
        if session is None:
            raise SessionNotFoundError(session_id)
        session.current_context.update(context)
        session.expires_at = datetime.now(timezone.utc) + self._session_timeout
        return session

    async def delete_session(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    async def list_sessions(self, conversation_id: str | None = None) -> list[Session]:
        if conversation_id:
            return [s for s in self._sessions.values() if s.conversation_id == conversation_id]
        return list(self._sessions.values())

    async def cleanup_expired(self) -> int:
        now = datetime.now(timezone.utc)
        expired = [sid for sid, s in self._sessions.items() if s.expires_at and now > s.expires_at]
        for sid in expired:
            self._sessions.pop(sid, None)
        if expired:
            logger.info("session.cleanup", expired_count=len(expired))
        return len(expired)
