"""ConversationService — wiring conversation module with DI and event bus."""

from typing import Any, AsyncIterator

from aios.conversation.manager import ConversationManager
from aios.conversation.models import Conversation, Message
from aios.conversation.interfaces import IConversationService
from aios.conversation.exceptions import ConversationNotFoundError, AIProviderError
from aios.utils.logger import get_logger
from aios.utils.tracer import trace_async_gen

logger = get_logger(__name__)


class ConversationService(IConversationService):
    def __init__(
        self,
        manager: ConversationManager,
        event_bus: Any | None = None,
    ):
        self._manager = manager
        self._event_bus = event_bus

    async def create_conversation(
        self,
        title: str | None = None,
        project: str | None = None,
        provider_id: str | None = None,
        model_id: str | None = None,
    ) -> Conversation:
        conv = await self._manager.create_conversation(title, project, provider_id=provider_id, model_id=model_id)
        if self._event_bus:
            await self._event_bus.publish("conversation:created", {
                "id": conv.id,
                "title": conv.title,
            })
        return conv

    async def get_conversation(self, conversation_id: str) -> Conversation:
        try:
            return await self._manager.get_conversation(conversation_id)
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error("service.get_conversation_failed", error=str(e))
            raise

    async def list_conversations(self, limit: int = 50, offset: int = 0) -> list[Conversation]:
        return await self._manager.list_conversations(limit, offset)

    async def delete_conversation(self, conversation_id: str) -> None:
        await self._manager.delete_conversation(conversation_id)
        if self._event_bus:
            await self._event_bus.publish("conversation:deleted", {"id": conversation_id})

    async def rename_conversation(self, conversation_id: str, title: str) -> Conversation:
        conv = await self._manager.rename_conversation(conversation_id, title)
        if self._event_bus:
            await self._event_bus.publish("conversation:renamed", {
                "id": conv.id,
                "title": conv.title,
            })
        return conv

    async def send_message(self, conversation_id: str, content: str) -> Message:
        try:
            response = await self._manager.send_message(conversation_id, content)
            if self._event_bus:
                await self._event_bus.publish("message:sent", {
                    "conversation_id": conversation_id,
                    "user_message": content[:100],
                    "response_id": response.id,
                })
            return response
        except ConversationNotFoundError:
            raise
        except AIProviderError:
            raise
        except Exception as e:
            logger.error("service.send_message_failed", error=str(e))
            raise

    async def set_provider_model(
        self,
        conversation_id: str,
        provider_id: str | None = None,
        model_id: str | None = None,
        routing_policy: str | None = None,
    ) -> Conversation:
        try:
            return await self._manager.set_provider_model(conversation_id, provider_id, model_id, routing_policy=routing_policy)
        except ConversationNotFoundError:
            raise
        except Exception as e:
            logger.error("service.set_provider_model_failed", error=str(e))
            raise

    @trace_async_gen
    async def stream_message(self, conversation_id: str, content: str) -> AsyncIterator[dict]:
        try:
            async for event in self._manager.stream_message(conversation_id, content):
                yield event
        except ConversationNotFoundError:
            yield {"type": "error", "data": {"error": "Conversation not found", "recoverable": False}}
        except Exception as e:
            logger.error("service.stream_message_failed", error=str(e))
            yield {"type": "error", "data": {"error": str(e), "recoverable": True}}

    async def get_history(self, conversation_id: str, limit: int = 100, offset: int = 0) -> list[Message]:
        return await self._manager.get_history(conversation_id, limit, offset)

    async def clear_history(self, conversation_id: str) -> None:
        await self._manager.clear_history(conversation_id)
        if self._event_bus:
            await self._event_bus.publish("conversation:history_cleared", {"id": conversation_id})
