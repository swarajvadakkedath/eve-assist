"""File-based conversation repository with atomic saves and crash recovery."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import structlog

from aios.conversation.models import Conversation, Message, MessageRole
from aios.conversation.interfaces import IConversationRepository

logger = structlog.get_logger(__name__)


class FileConversationRepository(IConversationRepository):
    """Persists conversations as individual JSON files with atomic writes.

    Layout:
        ~/.eve/conversations/
            index.json          # conversation index (id → metadata)
            {conv_id}/
                conversation.json  # Conversation metadata
                messages.jsonl     # Messages in JSONL format
    """

    def __init__(self, base_dir: str | None = None):
        if base_dir is None:
            base_dir = str(Path.home() / ".eve" / "conversations")
        self._base_dir = Path(base_dir)
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _conv_dir(self, conv_id: str) -> Path:
        return self._base_dir / conv_id

    def _conv_file(self, conv_id: str) -> Path:
        return self._conv_dir(conv_id) / "conversation.json"

    def _messages_file(self, conv_id: str) -> Path:
        return self._conv_dir(conv_id) / "messages.jsonl"

    def _atomic_write(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            os.replace(tmp_path, str(path))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _conv_to_dict(self, conv: Conversation) -> dict:
        return {
            "id": conv.id,
            "title": conv.title,
            "created_at": conv.created_at.isoformat() if conv.created_at else None,
            "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
            "active_project": conv.active_project,
            "is_active": conv.is_active,
            "mode": conv.mode,
            "metadata": conv.metadata,
            "message_count": conv.message_count,
            "parent_id": conv.parent_id,
            "branch_point_message_id": conv.branch_point_message_id,
            "provider_id": conv.provider_id,
            "model_id": conv.model_id,
            "temperature": conv.temperature,
            "top_p": conv.top_p,
            "top_k": conv.top_k,
            "max_tokens": conv.max_tokens,
            "system_prompt": conv.system_prompt,
            "thinking_mode": conv.thinking_mode,
            "streaming_enabled": conv.streaming_enabled,
        }

    def _dict_to_conv(self, data: dict) -> Conversation:
        return Conversation(
            id=data.get("id", ""),
            title=data.get("title", ""),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
            active_project=data.get("active_project"),
            is_active=data.get("is_active", True),
            mode=data.get("mode", "chat"),
            metadata=data.get("metadata", {}),
            message_count=data.get("message_count", 0),
            parent_id=data.get("parent_id"),
            branch_point_message_id=data.get("branch_point_message_id"),
            provider_id=data.get("provider_id"),
            model_id=data.get("model_id"),
            temperature=data.get("temperature"),
            top_p=data.get("top_p"),
            top_k=data.get("top_k"),
            max_tokens=data.get("max_tokens"),
            system_prompt=data.get("system_prompt"),
            thinking_mode=data.get("thinking_mode", False),
            streaming_enabled=data.get("streaming_enabled", True),
        )

    def _message_to_dict(self, msg: Message) -> dict:
        d = {
            "id": msg.id,
            "conversation_id": msg.conversation_id,
            "role": msg.role.value if isinstance(msg.role, MessageRole) else msg.role,
            "content": msg.content,
            "timestamp": msg.timestamp.isoformat() if hasattr(msg.timestamp, "isoformat") else msg.timestamp,
            "tokens_used": msg.tokens_used,
            "tool_calls": [
                tc.__dict__ if hasattr(tc, "__dict__") else tc for tc in msg.tool_calls
            ],
            "tool_results": msg.tool_results,
            "attachments": msg.attachments,
            "metadata": msg.metadata,
            "is_regenerated": msg.is_regenerated,
            "latency_ms": msg.latency_ms,
        }
        if msg.edit_history:
            d["edit_history"] = [
                {
                    "original_content": e.original_content,
                    "edited_content": e.edited_content,
                    "timestamp": e.timestamp.isoformat() if hasattr(e.timestamp, "isoformat") else str(e.timestamp),
                    "regenerated": e.regenerated,
                }
                for e in msg.edit_history
            ]
        if msg.planning_context:
            d["planning_context"] = {
                "intent": msg.planning_context.intent,
                "selected_capabilities": msg.planning_context.selected_capabilities,
                "planning_time_ms": msg.planning_context.planning_time_ms,
                "planner_version": msg.planning_context.planner_version,
            }
        if msg.execution_context:
            ctx = msg.execution_context
            d["execution_context"] = {
                "execution_id": ctx.execution_id,
                "status": ctx.status,
                "current_step": ctx.current_step,
                "completed_steps": ctx.completed_steps,
                "total_steps": ctx.total_steps,
                "progress": ctx.progress,
                "started_at": ctx.started_at.isoformat() if hasattr(ctx.started_at, "isoformat") else ctx.started_at,
                "completed_at": ctx.completed_at.isoformat() if hasattr(ctx.completed_at, "isoformat") else ctx.completed_at,
                "duration_ms": ctx.duration_ms,
                "error": ctx.error,
                "cancelled": ctx.cancelled,
                "tools_executed": ctx.tools_executed,
                "capabilities_used": ctx.capabilities_used,
                "retry_count": ctx.retry_count,
                "permission_requests": ctx.permission_requests,
                "warnings": ctx.warnings,
            }
        return d

    def _dict_to_message(self, data: dict) -> Message:
        from aios.conversation.models import EditEntry, PlanningContext, ExecutionContext

        edit_history = []
        for eh in data.get("edit_history") or []:
            edit_history.append(EditEntry(
                original_content=eh.get("original_content", ""),
                edited_content=eh.get("edited_content", ""),
                timestamp=eh.get("timestamp", ""),
                regenerated=eh.get("regenerated", False),
            ))

        planning_ctx = None
        if data.get("planning_context"):
            pc = data["planning_context"]
            planning_ctx = PlanningContext(
                intent=pc.get("intent"),
                selected_capabilities=pc.get("selected_capabilities", []),
                planning_time_ms=pc.get("planning_time_ms"),
                planner_version=pc.get("planner_version"),
            )

        execution_ctx = None
        if data.get("execution_context"):
            ec = data["execution_context"]
            execution_ctx = ExecutionContext(
                execution_id=ec.get("execution_id"),
                status=ec.get("status"),
                current_step=ec.get("current_step", 0),
                completed_steps=ec.get("completed_steps", 0),
                total_steps=ec.get("total_steps", 0),
                progress=ec.get("progress", 0.0),
                started_at=ec.get("started_at"),
                completed_at=ec.get("completed_at"),
                duration_ms=ec.get("duration_ms"),
                error=ec.get("error"),
                cancelled=ec.get("cancelled", False),
                tools_executed=ec.get("tools_executed", []),
                capabilities_used=ec.get("capabilities_used", []),
                retry_count=ec.get("retry_count", 0),
                permission_requests=ec.get("permission_requests", 0),
                warnings=ec.get("warnings", []),
            )

        return Message(
            id=data.get("id", ""),
            conversation_id=data.get("conversation_id", ""),
            role=data.get("role", "user"),
            content=data.get("content", ""),
            timestamp=data.get("timestamp", ""),
            tokens_used=data.get("tokens_used", 0),
            tool_calls=data.get("tool_calls", []),
            tool_results=data.get("tool_results", []),
            attachments=data.get("attachments", []),
            metadata=data.get("metadata", {}),
            edit_history=edit_history,
            is_regenerated=data.get("is_regenerated", False),
            latency_ms=data.get("latency_ms", 0.0),
            planning_context=planning_ctx,
            execution_context=execution_ctx,
        )

    async def create_conversation(self, conversation: Conversation) -> Conversation:
        conv_dir = self._conv_dir(conversation.id)
        conv_dir.mkdir(parents=True, exist_ok=True)
        data = self._conv_to_dict(conversation)
        self._atomic_write(self._conv_file(conversation.id), data)
        self._update_index(conversation.id, data)
        logger.debug("repo.conversation_created", conv_id=conversation.id)
        return conversation

    async def get_conversation(self, conversation_id: str) -> Conversation | None:
        conv_file = self._conv_file(conversation_id)
        if not conv_file.exists():
            return None
        try:
            data = json.loads(conv_file.read_text("utf-8"))
            return self._dict_to_conv(data)
        except (json.JSONDecodeError, KeyError, OSError) as e:
            logger.error("repo.load_failed", conv_id=conversation_id, error=str(e))
            return None

    async def update_conversation(self, conversation: Conversation) -> Conversation:
        conv_file = self._conv_file(conversation.id)
        if not conv_file.exists():
            return await self.create_conversation(conversation)
        try:
            data = json.loads(conv_file.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            data = {}
        data.update(self._conv_to_dict(conversation))
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        self._atomic_write(conv_file, data)
        self._update_index(conversation.id, data)
        return conversation

    async def delete_conversation(self, conversation_id: str) -> None:
        conv_dir = self._conv_dir(conversation_id)
        if conv_dir.exists():
            shutil.rmtree(str(conv_dir))
        self._remove_from_index(conversation_id)

    async def list_conversations(self, limit: int = 50, offset: int = 0) -> list[Conversation]:
        conversations = []
        index_path = self._base_dir / "index.json"
        if index_path.exists():
            try:
                entries = json.loads(index_path.read_text("utf-8"))
                for conv_id in entries:
                    conv = await self.get_conversation(conv_id)
                    if conv:
                        conversations.append(conv)
                conversations.sort(key=lambda c: c.updated_at or datetime.min, reverse=True)
                return conversations[offset: offset + limit]
            except (json.JSONDecodeError, OSError):
                pass
        for item in self._base_dir.iterdir():
            if item.is_dir() and (item / "conversation.json").exists():
                conv = await self.get_conversation(item.name)
                if conv:
                    conversations.append(conv)
        conversations.sort(key=lambda c: c.updated_at or datetime.min, reverse=True)
        return conversations[offset: offset + limit]

    async def add_message(self, message: Message) -> Message:
        conv_id = message.conversation_id
        message_file = self._messages_file(conv_id)
        message_file.parent.mkdir(parents=True, exist_ok=True)
        line = json.dumps(self._message_to_dict(message), default=str) + "\n"
        fd, tmp_path = tempfile.mkstemp(dir=str(message_file.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "a", encoding="utf-8") as f:
                if message_file.exists():
                    f.write(message_file.read_text("utf-8"))
                f.write(line)
            os.replace(tmp_path, str(message_file))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        return message

    async def get_messages(self, conversation_id: str, limit: int = 100, offset: int = 0) -> list[Message]:
        message_file = self._messages_file(conversation_id)
        if not message_file.exists():
            return []
        messages = []
        try:
            for line in message_file.read_text("utf-8").strip().split("\n"):
                if not line.strip():
                    continue
                try:
                    data = json.loads(line)
                    messages.append(self._dict_to_message(data))
                except json.JSONDecodeError:
                    continue
        except OSError as e:
            logger.error("repo.read_messages_failed", conv_id=conversation_id, error=str(e))
            return []
        return messages[offset: offset + limit]

    async def clear_history(self, conversation_id: str) -> None:
        message_file = self._messages_file(conversation_id)
        if message_file.exists():
            message_file.unlink()

    def _update_index(self, conv_id: str, data: dict) -> None:
        index_path = self._base_dir / "index.json"
        try:
            if index_path.exists():
                index = json.loads(index_path.read_text("utf-8"))
            else:
                index = {}
            index[conv_id] = {
                "id": conv_id,
                "title": data.get("title", ""),
                "updated_at": data.get("updated_at", ""),
            }
            self._atomic_write(index_path, index)
        except (json.JSONDecodeError, OSError):
            pass

    def _remove_from_index(self, conv_id: str) -> None:
        index_path = self._base_dir / "index.json"
        try:
            if index_path.exists():
                index = json.loads(index_path.read_text("utf-8"))
                index.pop(conv_id, None)
                self._atomic_write(index_path, index)
        except (json.JSONDecodeError, OSError):
            pass

    def recover(self) -> int:
        """Recover conversations from disk after a crash.

        Returns the number of conversations recovered.
        """
        count = 0
        for item in self._base_dir.iterdir():
            if not item.is_dir():
                continue
            conv_file = item / "conversation.json"
            msg_file = item / "messages.jsonl"
            if conv_file.exists():
                count += 1
            elif msg_file.exists():
                logger.warning("repo.orphaned_messages", conv_id=item.name)
        logger.info("repo.recovery_complete", recovered=count)
        return count
