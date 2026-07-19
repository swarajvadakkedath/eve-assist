"""Abstract interfaces for the conversation module."""

from abc import ABC, abstractmethod
from typing import AsyncIterator

from aios.conversation.models import Conversation, Message, Session


class IConversationRepository(ABC):
    @abstractmethod
    async def create_conversation(self, conversation: Conversation) -> Conversation: ...

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Conversation | None: ...

    @abstractmethod
    async def list_conversations(self, limit: int = 50, offset: int = 0) -> list[Conversation]: ...

    @abstractmethod
    async def update_conversation(self, conversation: Conversation) -> Conversation: ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> None: ...

    @abstractmethod
    async def add_message(self, message: Message) -> Message: ...

    @abstractmethod
    async def get_messages(self, conversation_id: str, limit: int = 100, offset: int = 0) -> list[Message]: ...

    @abstractmethod
    async def clear_history(self, conversation_id: str) -> None: ...


class IConversationService(ABC):
    @abstractmethod
    async def create_conversation(self, title: str | None = None, project: str | None = None) -> Conversation: ...

    @abstractmethod
    async def get_conversation(self, conversation_id: str) -> Conversation: ...

    @abstractmethod
    async def list_conversations(self, limit: int = 50, offset: int = 0) -> list[Conversation]: ...

    @abstractmethod
    async def delete_conversation(self, conversation_id: str) -> None: ...

    @abstractmethod
    async def rename_conversation(self, conversation_id: str, title: str) -> Conversation: ...

    @abstractmethod
    async def send_message(self, conversation_id: str, content: str) -> Message: ...

    @abstractmethod
    async def stream_message(self, conversation_id: str, content: str) -> AsyncIterator[dict]: ...

    @abstractmethod
    async def get_history(self, conversation_id: str, limit: int = 100, offset: int = 0) -> list[Message]: ...

    @abstractmethod
    async def clear_history(self, conversation_id: str) -> None: ...
