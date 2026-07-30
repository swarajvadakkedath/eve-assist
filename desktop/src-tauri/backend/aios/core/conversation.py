"""Conversation System — chat, voice, hybrid modes."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import AsyncIterator
from uuid import uuid4


@dataclass
class Conversation:
    id: str = ""
    title: str = ""
    mode: str = "chat"  # chat, voice, hybrid
    created_at: datetime = None
    updated_at: datetime = None
    is_active: bool = True

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        now = datetime.now(timezone.utc)
        if not self.created_at:
            self.created_at = now
            self.updated_at = now


@dataclass
class Message:
    id: str = ""
    conversation_id: str = ""
    role: str = "user"  # user, assistant, system
    content: str = ""
    timestamp: datetime = None
    tokens_used: int = 0
    metadata: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = uuid4().hex
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc)


class StreamEvent:
    TOKEN = "token"
    DONE = "done"
    ERROR = "error"


class ConversationSystem:
    def __init__(self):
        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[Message]] = {}

    async def send_message(self, content: str, mode: str = "chat") -> Message:
        conv_id = self._get_or_create_conversation(mode)
        msg = Message(conversation_id=conv_id, role="user", content=content)
        self._messages.setdefault(conv_id, []).append(msg)
        response = Message(conversation_id=conv_id, role="assistant", content="I'm processing your request", tokens_used=0)
        self._messages[conv_id].append(response)
        return response

    async def stream_message(self, content: str) -> AsyncIterator[dict]:
        yield {"type": StreamEvent.TOKEN, "content": "Processing..."}
        yield {"type": StreamEvent.DONE, "message_id": uuid4().hex}

    async def get_history(self, conversation_id: str) -> list[Message]:
        return self._messages.get(conversation_id, [])

    async def create_conversation(self, title: str | None = None) -> Conversation:
        conv = Conversation(title=title or "New Conversation")
        self._conversations[conv.id] = conv
        return conv

    async def delete_conversation(self, conversation_id: str) -> None:
        self._conversations.pop(conversation_id, None)
        self._messages.pop(conversation_id, None)

    async def switch_mode(self, mode: str) -> None:
        valid_modes = {"chat", "voice", "hybrid"}
        if mode not in valid_modes:
            raise ValueError(f"Invalid mode: {mode}. Must be one of {valid_modes}")

    def _get_or_create_conversation(self, mode: str) -> str:
        active = [c for c in self._conversations.values() if c.is_active]
        if active:
            return active[0].id
        conv = Conversation(mode=mode)
        self._conversations[conv.id] = conv
        return conv.id
