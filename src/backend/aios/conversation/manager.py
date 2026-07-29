"""ConversationManager — single entry point for all conversations."""

import asyncio
import time
from datetime import datetime
from typing import Any, AsyncIterator
from uuid import uuid4

from aios.conversation.models import (
    Conversation,
    Message,
    MessageRole,
    ToolCall,
    ToolCallStatus,
    StreamEventType,
    EditEntry,
    PlanningContext,
    ExecutionContext,
)
from aios.execution.models import ExecutionStatus
from aios.conversation.interfaces import IConversationService
from aios.conversation.exceptions import (
    ConversationNotFoundError,
    MessageNotFoundError,
    AIProviderError,
    MemoryError,
    StreamError,
)
from aios.conversation.prompts import (
    build_system_prompt,
    build_memory_context,
    build_tool_descriptions,
    messages_to_llm_format,
)
from aios.conversation.formatter import (
    create_token_event,
    create_done_event,
    create_error_event,
    create_tool_call_event,
    create_tool_result_event,
    create_status_event,
    create_planner_started_event,
    create_planner_completed_event,
    create_memory_retrieval_event,
    create_tool_requested_event,
    create_tool_running_event,
    create_tool_completed_event,
    create_context_loaded_event,
    create_final_response_event,
    create_title_generated_event,
    create_analytics_event,
)
from aios.conversation.stream import StreamManager
from aios.conversation.session import SessionManager
from aios.conversation.history import HistoryManager
from aios.conversation.titles import TitleGenerator
from aios.conversation.search import ConversationSearch, SearchResult
from aios.conversation.branching import BranchManager
from aios.conversation.analytics import AnalyticsTracker, ConversationAnalytics
from aios.conversation.export import ConversationExporter
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class ConversationManager(IConversationService):
    def __init__(
        self,
        ai_router: Any | None = None,
        memory_system: Any | None = None,
        planner: Any | None = None,
        tool_manager: Any | None = None,
        capability_registry: Any | None = None,
        context_engine: Any | None = None,
        repository: Any | None = None,
        execution_engine: Any | None = None,
    ):
        self._ai_router = ai_router
        self._memory = memory_system
        self._planner = planner
        self._tool_manager = tool_manager
        self._capability_registry = capability_registry
        self._context_engine = context_engine
        self._repository = repository
        self._execution_engine = execution_engine

        self._conversations: dict[str, Conversation] = {}
        self._messages: dict[str, list[Message]] = {}

        self._session_manager = SessionManager()
        self._history_manager = HistoryManager()
        self._stream_manager = StreamManager()
        self._title_generator = TitleGenerator(ai_router)
        self._search = ConversationSearch()
        self._branch_manager = BranchManager()
        self._analytics = AnalyticsTracker()
        self._exporter = ConversationExporter()

    # ── Conversation CRUD ──────────────────────────────────────────

    async def create_conversation(self, title: str | None = None, project: str | None = None) -> Conversation:
        conv = Conversation(
            title=title or "New Conversation",
            active_project=project,
        )
        if title:
            conv.metadata["title_is_custom"] = True
        self._conversations[conv.id] = conv

        if self._repository:
            try:
                await self._repository.create_conversation(conv)
            except Exception as e:
                logger.error("conversation.repository_create_failed", error=str(e))

        session = await self._session_manager.create_session(conv.id)
        logger.info("conversation.created", id=conv.id, title=conv.title)
        return conv

    async def get_conversation(self, conversation_id: str) -> Conversation:
        conv = self._conversations.get(conversation_id)
        if conv is None and self._repository:
            try:
                conv = await self._repository.get_conversation(conversation_id)
                if conv:
                    self._conversations[conv.id] = conv
            except Exception as e:
                logger.error("conversation.repository_get_failed", error=str(e))
        if conv is None:
            raise ConversationNotFoundError(conversation_id)
        return conv

    async def list_conversations(self, limit: int = 50, offset: int = 0) -> list[Conversation]:
        convs = list(self._conversations.values())
        convs.sort(key=lambda c: c.updated_at or datetime.min, reverse=True)
        return convs[offset : offset + limit]

    async def delete_conversation(self, conversation_id: str) -> None:
        self._conversations.pop(conversation_id, None)
        self._messages.pop(conversation_id, None)
        if self._repository:
            try:
                await self._repository.delete_conversation(conversation_id)
            except Exception as e:
                logger.error("conversation.repository_delete_failed", error=str(e))
        await self._search.clear_index(conversation_id)
        logger.info("conversation.deleted", id=conversation_id)

    async def rename_conversation(self, conversation_id: str, title: str) -> Conversation:
        conv = await self.get_conversation(conversation_id)
        conv.title = title
        conv.updated_at = datetime.utcnow()
        conv.metadata["title_is_custom"] = True
        if self._repository:
            try:
                await self._repository.update_conversation(conv)
            except Exception as e:
                logger.error("conversation.repository_rename_failed", error=str(e))
        return conv

    # ── Smart Titles ───────────────────────────────────────────────

    async def ensure_title(self, conversation_id: str) -> str | None:
        conv = await self.get_conversation(conversation_id)
        if conv.title and conv.title != "New Conversation" and conv.metadata.get("title_is_custom"):
            return conv.title
        if conv.title and conv.title != "New Conversation":
            return conv.title
        messages = self._messages.get(conversation_id, [])
        new_title = await self._title_generator.generate_title(conv, messages)
        if new_title:
            conv.title = new_title
            conv.updated_at = datetime.utcnow()
            logger.info("conversation.title_generated", id=conversation_id, title=new_title)
        return conv.title

    # ── Search ─────────────────────────────────────────────────────

    async def search_conversations(self, query: str, limit: int = 20) -> list[SearchResult]:
        convs = list(self._conversations.values())
        return await self._search.search_conversations(query, convs, self._messages, limit)

    async def reindex_conversation(self, conversation_id: str):
        conv = await self.get_conversation(conversation_id)
        messages = self._messages.get(conversation_id, [])
        await self._search.index_conversation(conv, messages)

    # ── Branching ──────────────────────────────────────────────────

    async def create_branch(
        self,
        conversation_id: str,
        branch_point_message_id: str,
        title: str | None = None,
    ) -> Conversation:
        parent = await self.get_conversation(conversation_id)
        branch = await self._branch_manager.create_branch(parent, branch_point_message_id, title)
        messages = self._messages.get(conversation_id, [])
        copied = await self._branch_manager.copy_messages_to_branch(
            messages, branch_point_message_id, branch.id,
        )
        self._conversations[branch.id] = branch
        self._messages[branch.id] = copied
        logger.info("branch.created", branch_id=branch.id, parent_id=conversation_id)
        return branch

    async def get_branches(self, conversation_id: str) -> list[Conversation]:
        branches = await self._branch_manager.get_branches(conversation_id)
        result = []
        for b in branches:
            cached = self._conversations.get(b.id)
            result.append(cached or b)
        return result

    async def delete_branch(self, branch_id: str) -> bool:
        if await self._branch_manager.delete_branch(branch_id):
            self._conversations.pop(branch_id, None)
            self._messages.pop(branch_id, None)
            return True
        return False

    async def rename_branch(self, branch_id: str, title: str) -> bool:
        conv = self._conversations.get(branch_id)
        if conv:
            conv.title = title
            conv.updated_at = datetime.utcnow()
        return await self._branch_manager.rename_branch(branch_id, title)

    # ── Edit & Regenerate ──────────────────────────────────────────

    async def edit_message(
        self,
        conversation_id: str,
        message_id: str,
        new_content: str,
    ) -> Message:
        messages = self._messages.get(conversation_id, [])
        target_idx = None
        for i, msg in enumerate(messages):
            if msg.id == message_id:
                target_idx = i
                break

        if target_idx is None:
            raise MessageNotFoundError(message_id)

        target = messages[target_idx]
        edit_entry = EditEntry(
            original_content=target.content,
            edited_content=new_content,
            timestamp=datetime.utcnow(),
        )
        target.edit_history.append(edit_entry)
        target.content = new_content

        messages[target_idx + 1:] = []

        conv = await self.get_conversation(conversation_id)
        conv.updated_at = datetime.utcnow()
        logger.info("message.edited", conversation_id=conversation_id, message_id=message_id)
        return target

    async def regenerate_message(
        self,
        conversation_id: str,
        message_id: str,
    ) -> Message:
        conv = await self.get_conversation(conversation_id)
        messages = self._messages.get(conversation_id, [])
        target_idx = None

        for i, msg in enumerate(messages):
            if msg.id == message_id:
                target_idx = i
                break

        if target_idx is None:
            raise MessageNotFoundError(message_id)

        messages[target_idx:] = []

        context = await self._gather_context(conversation_id)
        memories = await self._retrieve_memories(" ".join(m.content for m in messages[-3:] if m.role == MessageRole.USER), conversation_id)
        history = self._messages.get(conversation_id, [])
        context_window = await self._history_manager.build_context_window(history, memories)

        llm_messages = messages_to_llm_format(
            context_window,
            system_prompt=build_system_prompt(conv, context),
            memory_context=build_memory_context(memories),
            tool_descriptions=build_tool_descriptions(await self._get_available_tools()),
        )

        try:
            ai_response = await self._ai_router.route(
                type("AIRequest", (), {
                    "messages": llm_messages,
                    "stream": False,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                })()
            )
        except Exception as e:
            raise AIProviderError(f"AI provider failed: {e}", original=e)

        new_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=ai_response.content,
            tokens_used=ai_response.tokens_used,
            is_regenerated=True,
        )
        self._add_message(conversation_id, new_msg)
        conv.updated_at = datetime.utcnow()
        logger.info("message.regenerated", conversation_id=conversation_id, message_id=message_id)
        return new_msg

    # ── Analytics ──────────────────────────────────────────────────

    async def get_conversation_analytics(self, conversation_id: str) -> dict:
        return await self._analytics.get_conversation_summary(conversation_id)

    async def get_conversation_analytics_detail(self, conversation_id: str) -> list[ConversationAnalytics]:
        return await self._analytics.get_conversation_analytics(conversation_id)

    # ── Export ─────────────────────────────────────────────────────

    async def export_conversation(
        self,
        conversation_id: str,
        format: str = "markdown",
    ) -> str:
        conv = await self.get_conversation(conversation_id)
        messages = self._messages.get(conversation_id, [])
        if format == "html":
            return await self._exporter.export_html(conv, messages)
        elif format == "json":
            return await self._exporter.export_json(conv, messages)
        else:
            return await self._exporter.export_markdown(conv, messages)

    # ── Message Operations ─────────────────────────────────────────

    async def send_message(self, conversation_id: str, content: str) -> Message:
        conv = await self.get_conversation(conversation_id)
        start_time = time.monotonic()
        intent = await self._detect_intent(content)

        user_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
        )
        self._add_message(conversation_id, user_msg)
        if self._repository:
            try:
                await self._repository.add_message(user_msg)
            except Exception as e:
                logger.error("conversation.repository_add_message_failed", error=str(e))

        context = await self._safe_gather_context(conversation_id)
        memories = await self._safe_retrieve_memories(content, conversation_id)
        
        plan = None
        selected_capabilities = []
        execution_ctx = None
        if intent not in ["conversation", "question"]:
            plan = await self._planner.create_plan(content, context)
            if plan and plan.steps:
                selected_capabilities = [step.capability for step in plan.steps]
                
                if self._execution_engine:
                    execution = await self._execution_engine.execute_plan(
                        plan, content, conversation_id
                    )
                    await self._execution_engine.wait_for_execution(execution.id)
                    result = await self._execution_engine.get_execution_result(execution.id)
                    progress = await self._execution_engine.get_execution_progress(execution.id)
                    execution_ctx = ExecutionContext(
                        execution_id=execution.id,
                        status=execution.status.value,
                        current_step=progress.completed_tasks,
                        completed_steps=progress.completed_tasks,
                        total_steps=progress.total_tasks,
                        progress=progress.percentage,
                        error=result.errors[0] if result and result.errors else None,
                        started_at=execution.started_at,
                        completed_at=execution.completed_at,
                        duration_ms=result.duration_ms if result else None,
                        tools_executed=result.tools_executed if result else [],
                        capabilities_used=result.capabilities_used if result else [],
                        retry_count=result.retry_count if result else 0,
                        permission_requests=result.permission_requests if result else 0,
                        warnings=result.warnings if result else [],
                        cancelled=execution.status == ExecutionStatus.CANCELLED,
                    )

        history = self._messages.get(conversation_id, [])
        context_window = await self._history_manager.build_context_window(history, memories)

        llm_messages = messages_to_llm_format(
            context_window,
            system_prompt=build_system_prompt(conv, context),
            memory_context=build_memory_context(memories),
            tool_descriptions=build_tool_descriptions(await self._get_available_tools()),
        )

        try:
            ai_response = await self._ai_router.route(
                type("AIRequest", (), {
                    "messages": llm_messages,
                    "stream": False,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                })()
            )
        except Exception as e:
            raise AIProviderError(f"AI provider failed: {e}", original=e)

        latency_ms = (time.monotonic() - start_time) * 1000

        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=ai_response.content,
            tokens_used=ai_response.tokens_used,
            latency_ms=latency_ms,
            planning_context=PlanningContext(
                intent=intent,
                plan=plan,
                selected_capabilities=selected_capabilities,
            ),
            execution_context=execution_ctx,
        )

        self._add_message(conversation_id, assistant_msg)
        if self._repository:
            try:
                await self._repository.add_message(assistant_msg)
            except Exception as e:
                logger.error("conversation.repository_add_response_failed", error=str(e))

        await self._update_memory(content, ai_response.content, conversation_id)
        conv.updated_at = datetime.utcnow()
        conv.message_count = len(self._messages.get(conversation_id, [])) // 2

        await self.ensure_title(conversation_id)
        await self.reindex_conversation(conversation_id)

        return assistant_msg

    async def stream_message(self, conversation_id: str, content: str) -> AsyncIterator[dict]:
        conv = await self.get_conversation(conversation_id)
        start_time = time.monotonic()
        intent = await self._detect_intent(content)

        user_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.USER,
            content=content,
        )
        self._add_message(conversation_id, user_msg)
        if self._repository:
            try:
                await self._repository.add_message(user_msg)
            except Exception as e:
                logger.error("conversation.repository_add_message_failed", error=str(e))

        yield create_status_event("understanding", f"Detected intent: {intent}")

        context = await self._safe_gather_context(conversation_id)
        memories = await self._safe_retrieve_memories(content, conversation_id)
        
        plan = None
        selected_capabilities = []
        execution_ctx = None
        if intent not in ["conversation", "question"]:
            plan = await self._safe_create_plan(content, context)
            if plan and plan.steps:
                selected_capabilities = [step.capability for step in plan.steps]
                yield create_planner_started_event(content)
                yield create_planner_completed_event(len(plan.steps))

                if self._execution_engine:
                    execution = await self._execution_engine.execute_plan(plan, content, conversation_id)

                    async for event in self._execution_engine.stream_events(execution.id):
                        yield create_status_event("executing_tool", str(event))

                    result = await self._execution_engine.get_execution_result(execution.id)
                    progress = await self._execution_engine.get_execution_progress(execution.id)
                    execution_ctx = ExecutionContext(
                        execution_id=execution.id,
                        status=execution.status.value,
                        current_step=progress.completed_tasks,
                        completed_steps=progress.completed_tasks,
                        total_steps=progress.total_tasks,
                        progress=progress.percentage,
                        error=result.errors[0] if result and result.errors else None,
                        started_at=execution.started_at,
                        completed_at=execution.completed_at,
                        duration_ms=result.duration_ms if result else None,
                        tools_executed=result.tools_executed if result else [],
                        capabilities_used=result.capabilities_used if result else [],
                        retry_count=result.retry_count if result else 0,
                        permission_requests=result.permission_requests if result else 0,
                        warnings=result.warnings if result else [],
                        cancelled=execution.status == ExecutionStatus.CANCELLED,
                    )

                    if plan and plan.steps:
                        for step in plan.steps:
                            yield create_tool_requested_event(step.capability, step.capability)
                            yield create_tool_running_event(step.capability)
                            step_success = execution_ctx is not None and execution_ctx.error is None
                            step_duration = (execution_ctx.duration_ms or 0) / max(len(plan.steps), 1) if execution_ctx else 0
                            yield create_tool_completed_event(step.capability, step_success, step_duration)


        history = self._messages.get(conversation_id, [])
        context_window = await self._history_manager.build_context_window(history, memories)

        llm_messages = messages_to_llm_format(
            context_window,
            system_prompt=build_system_prompt(conv, context),
            memory_context=build_memory_context(memories),
            tool_descriptions=build_tool_descriptions(await self._safe_list_tools()),
        )

        yield create_final_response_event()
        yield create_status_event("generating", "Generating response...")

        full_content = ""
        tokens_used = 0

        try:
            token_gen = self._ai_router.route_stream(
                type("AIRequest", (), {
                    "messages": llm_messages,
                    "stream": True,
                    "max_tokens": 4096,
                    "temperature": 0.7,
                })()
            )

            async for event in self._stream_manager.stream(uuid4().hex, token_gen):
                if event["type"] == StreamEventType.TOKEN.value:
                    full_content += event["data"]["token"]
                    tokens_used += 1
                yield event

        except Exception as e:
            logger.error("stream.failed", error=str(e))
            yield create_error_event(str(e), recoverable=True)
            full_content = full_content or f"I encountered an error: {e}"

        latency_ms = (time.monotonic() - start_time) * 1000

        assistant_msg = Message(
            conversation_id=conversation_id,
            role=MessageRole.ASSISTANT,
            content=full_content,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            planning_context=PlanningContext(
                intent=intent,
                plan=plan,
                selected_capabilities=selected_capabilities,
            ),
            execution_context=execution_ctx,
        )

        self._add_message(conversation_id, assistant_msg)
        if self._repository:
            try:
                await self._repository.add_message(assistant_msg)
            except Exception as e:
                logger.error("conversation.repository_add_stream_failed", error=str(e))

        await self._safe_update_memory(content, full_content, conversation_id)
        conv.updated_at = datetime.utcnow()
        conv.message_count = len(self._messages.get(conversation_id, [])) // 2

        await self.ensure_title(conversation_id)
        await self.reindex_conversation(conversation_id)

    async def get_history(self, conversation_id: str, limit: int = 100, offset: int = 0) -> list[Message]:
        messages = self._messages.get(conversation_id, [])
        return messages[-limit:]

    async def clear_history(self, conversation_id: str) -> None:
        self._messages[conversation_id] = []
        if self._repository:
            try:
                await self._repository.clear_history(conversation_id)
            except Exception as e:
                logger.error("conversation.clear_history_failed", error=str(e))

    # ── Internal Helpers ───────────────────────────────────────────

    async def _detect_intent(self, content: str) -> str:
        content_lower = content.lower()
        if any(word in content_lower for word in ["what", "who", "where", "when", "why", "how"]):
            return "question"
        
        tool_keywords = {
            "workflow": ["workflow", "automate", "process"],
            "browser": ["browser", "web", "http", "download"],
            "file": ["file", "read", "write", "create", "delete", "directory"],
            "git": ["git", "repository", "commit", "push", "pull", "branch"],
            "desktop": ["desktop", "window", "tray", "notification"],
            "research": ["research", "analyze", "summarize"]
        }
        
        for intent, keywords in tool_keywords.items():
            if any(kw in content_lower for kw in keywords):
                return intent
                
        if any(kw in content_lower for kw in ["run", "execute", "tool"]):
            return "tool_execution"
            
        return "conversation"

    def _add_message(self, conversation_id: str, message: Message) -> None:
        self._messages.setdefault(conversation_id, []).append(message)

    async def _gather_context(self, conversation_id: str) -> dict:
        if not self._context_engine:
            return {}
        try:
            return {
                "active_app": await self._context_engine.get_active_app(),
                "active_file": await self._context_engine.get_active_file(),
                "project": await self._context_engine.detect_project(),
            }
        except Exception as e:
            logger.error("context.gather_failed", error=str(e))
            return {}

    async def _safe_gather_context(self, conversation_id: str) -> dict:
        try:
            return await self._gather_context(conversation_id)
        except Exception:
            return {}

    async def _retrieve_memories(self, query: str, conversation_id: str) -> list:
        if not self._memory:
            return []
        try:
            return await self._memory.search(query)
        except Exception as e:
            raise MemoryError(f"Memory retrieval failed: {e}", original=e)

    async def _safe_retrieve_memories(self, query: str, conversation_id: str) -> list:
        try:
            return await self._retrieve_memories(query, conversation_id)
        except Exception:
            return []

    async def _safe_create_plan(self, content: str, context: dict) -> Any | None:
        if not self._planner:
            return None
        try:
            return await self._planner.create_plan(content, context)
        except Exception:
            return None

    async def _get_available_tools(self) -> list:
        if not self._tool_manager:
            return []
        try:
            return await self._tool_manager.list_tools()
        except Exception:
            return []

    async def _safe_list_tools(self) -> list:
        try:
            return await self._get_available_tools()
        except Exception:
            return []

    async def _update_memory(self, user_input: str, response: str, conversation_id: str) -> None:
        if not self._memory:
            return
        try:
            from aios.core.memory_system import Memory, MemoryType
            memory = Memory(
                type=MemoryType.FACT,
                content=f"User: {user_input}\nAssistant: {response[:200]}",
                source="conversation",
                conversation_id=conversation_id,
                importance=0.5,
            )
            await self._memory.store(memory)
        except Exception as e:
            raise MemoryError(f"Memory update failed: {e}", original=e)

    async def _safe_update_memory(self, user_input: str, response: str, conversation_id: str) -> None:
        try:
            await self._update_memory(user_input, response, conversation_id)
        except Exception:
            pass
