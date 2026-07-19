"""Conversation branching — alternative paths from any message."""

from datetime import datetime
from typing import Any
from uuid import uuid4

from aios.conversation.models import Conversation, Message, MessageRole
from aios.conversation.exceptions import ConversationNotFoundError
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class BranchManager:
    def __init__(self):
        self._branches: dict[str, list[Conversation]] = {}

    async def create_branch(
        self,
        parent_conversation: Conversation,
        branch_point_message_id: str,
        title: str | None = None,
    ) -> Conversation:
        branch = Conversation(
            title=title or f"Branch of {parent_conversation.title[:30]}",
            active_project=parent_conversation.active_project,
            metadata={
                "parent_id": parent_conversation.id,
                "branch_point_message_id": branch_point_message_id,
                "is_branch": True,
            },
        )
        self._branches.setdefault(parent_conversation.id, []).append(branch)
        logger.info("branch.created",
                     branch_id=branch.id,
                     parent_id=parent_conversation.id,
                     branch_point=branch_point_message_id)
        return branch

    async def get_branches(self, conversation_id: str) -> list[Conversation]:
        return self._branches.get(conversation_id, [])

    async def get_parent_id(self, conversation: Conversation) -> str | None:
        return conversation.metadata.get("parent_id") if conversation.metadata else None

    async def get_branch_point(self, conversation: Conversation) -> str | None:
        return conversation.metadata.get("branch_point_message_id") if conversation.metadata else None

    async def is_branch(self, conversation: Conversation) -> bool:
        return bool(conversation.metadata and conversation.metadata.get("is_branch"))

    async def delete_branch(self, branch_id: str) -> bool:
        for parent_id, branches in self._branches.items():
            for i, b in enumerate(branches):
                if b.id == branch_id:
                    branches.pop(i)
                    logger.info("branch.deleted", branch_id=branch_id)
                    return True
        return False

    async def rename_branch(self, branch_id: str, title: str) -> bool:
        for parent_id, branches in self._branches.items():
            for b in branches:
                if b.id == branch_id:
                    b.title = title
                    b.updated_at = datetime.utcnow()
                    return True
        return False

    async def copy_messages_to_branch(
        self,
        messages: list[Message],
        branch_point_id: str,
        branch_id: str,
    ) -> list[Message]:
        copied = []
        for msg in messages:
            copied.append(Message(
                conversation_id=branch_id,
                role=msg.role,
                content=msg.content,
                attachments=list(msg.attachments),
                tool_calls=list(msg.tool_calls) if msg.tool_calls else [],
                tool_results=list(msg.tool_results) if msg.tool_results else [],
                metadata=dict(msg.metadata),
            ))
            if msg.id == branch_point_id:
                break
        return copied
