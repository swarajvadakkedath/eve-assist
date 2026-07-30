"""Smart conversation title generation."""

import re
from typing import Any

from aios.conversation.models import Conversation, Message, MessageRole
from aios.utils.logger import get_logger

logger = get_logger(__name__)

TITLE_MAX_LENGTH = 60

TITLE_PROMPT = """Generate a brief, descriptive title for this conversation (max 60 chars).

Conversation:
User: {user_message}
Assistant: {assistant_message}

Title:"""


class TitleGenerator:
    def __init__(self, ai_router: Any | None = None):
        self._ai_router = ai_router

    async def generate_title(
        self,
        conversation: Conversation,
        messages: list[Message],
    ) -> str | None:
        if conversation.title and conversation.metadata.get("title_is_custom"):
            return None

        user_msgs = [m for m in messages if m.role == MessageRole.USER]
        assistant_msgs = [m for m in messages if m.role == MessageRole.ASSISTANT]

        if not user_msgs:
            return None

        user_content = user_msgs[0].content[:200]
        assistant_content = assistant_msgs[0].content[:300] if assistant_msgs else ""

        if self._ai_router:
            try:
                title = await self._ai_title(user_content, assistant_content)
                if title:
                    return self._clean_title(title)
            except Exception as e:
                logger.error("title.ai_generation_failed", error=str(e))

        return self._fallback_title(user_content)

    async def generate_title_sync(
        self,
        conversation: Conversation,
        messages: list[Message],
    ) -> str | None:
        return await self.generate_title(conversation, messages)

    async def _ai_title(self, user_message: str, assistant_message: str) -> str | None:
        prompt = TITLE_PROMPT.format(
            user_message=user_message[:200],
            assistant_message=assistant_message[:300],
        )
        try:
            response = await self._ai_router.route(
                type("AIRequest", (), {
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "max_tokens": 30,
                    "temperature": 0.3,
                })()
            )
            return response.content.strip()
        except Exception:
            return None

    def _fallback_title(self, user_message: str) -> str:
        cleaned = re.sub(r'[^\w\s-]', '', user_message[:50])
        words = cleaned.split()
        if len(words) <= 3:
            return cleaned[:TITLE_MAX_LENGTH]
        title = ' '.join(words[:5])
        return title[:TITLE_MAX_LENGTH]

    def _clean_title(self, title: str) -> str:
        title = title.strip().strip('"').strip("'")
        title = re.sub(r'\s+', ' ', title)
        return title[:TITLE_MAX_LENGTH]
