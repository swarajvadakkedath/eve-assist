"""Phase C.8 P0 Hardening Tests.

Tests for:
  P0-1: Async context providers (ClipboardProvider, GitProvider)
  P0-2: ToolMediator enforcement in EveAgentAdapter
  P0-3: LLM tool-calling loop in ConversationManager
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from aios.core.context.providers.base import ClipboardProvider, GitProvider, WorkspaceProvider
from aios.core.context.models import ContextScope


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro)


# ---------------------------------------------------------------------------
# P0-1: Async Context Providers
# ---------------------------------------------------------------------------

class TestAsyncClipboardProvider:
    """ClipboardProvider must use async subprocess, never blocking."""

    def test_provider_id(self):
        p = ClipboardProvider()
        assert p.provider_id == "clipboard"

    def test_scope_is_private(self):
        p = ClipboardProvider()
        assert p.scope == ContextScope.PRIVATE

    @pytest.mark.asyncio
    async def test_collect_returns_dict(self):
        p = ClipboardProvider()
        # Force cache miss
        p._last_check = 0.0
        result = await p.collect()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_cache_hit_returns_empty(self):
        p = ClipboardProvider()
        p._last_check = 999999.0  # future timestamp → cache hit
        result = await p.collect()
        assert result == {}

    @pytest.mark.asyncio
    async def test_invalidate_cache(self):
        p = ClipboardProvider()
        p._last_check = 999999.0
        p.invalidate_cache()
        assert p._last_check == 0.0

    @pytest.mark.asyncio
    async def test_collect_uses_async_subprocess(self):
        """Verify collect() does not use synchronous subprocess.run."""
        p = ClipboardProvider()
        p._last_check = 0.0
        with patch("aios.core.context.providers.base.asyncio.create_subprocess_exec") as mock_proc:
            mock_proc.return_value = AsyncMock()
            mock_proc.return_value.communicate.return_value = (b"test clipboard", b"")
            mock_proc.return_value.returncode = 0
            result = await p.collect()
            mock_proc.assert_called_once()


class TestAsyncGitProvider:
    """GitProvider must use async subprocess, never blocking."""

    def test_provider_id(self):
        p = GitProvider()
        assert p.provider_id == "git"

    @pytest.mark.asyncio
    async def test_collect_no_repo_returns_empty(self):
        p = GitProvider()
        result = await p.collect()
        assert "git" in result

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached(self):
        p = GitProvider()
        p._repo_path = "/some/path"
        p._branch = "main"
        p._is_dirty = False
        p._remote_url = "origin"
        p._last_check = 999999.0
        result = await p.collect()
        assert result["git"]["current_branch"] == "main"

    @pytest.mark.asyncio
    async def test_collect_uses_async_subprocess(self):
        """Verify collect() uses asyncio.create_subprocess_exec."""
        p = GitProvider()
        p._repo_path = "/some/path"
        p._last_check = 0.0
        with patch("aios.core.context.providers.base.asyncio.create_subprocess_exec") as mock_proc, \
             patch("aios.core.context.providers.base.asyncio.wait_for") as mock_wait:
            mock_proc.return_value = AsyncMock()
            mock_wait.return_value = (b"main\n", b"")
            mock_proc.return_value.returncode = 0
            result = await p.collect()
            assert mock_proc.called


class TestWorkspaceAutoDetection:
    """WorkspaceProvider should auto-detect project type."""

    @pytest.mark.asyncio
    async def test_collect_with_workspace_path(self):
        p = WorkspaceProvider()
        p.set_workspace("E:\\Eve_Ai\\src")
        result = await p.collect()
        assert "workspace" in result
        # Should have detected project type from the path
        ws = result["workspace"]
        assert "workspace_path" in ws

    @pytest.mark.asyncio
    async def test_collect_empty_workspace(self):
        p = WorkspaceProvider()
        result = await p.collect()
        assert "workspace" in result
        ws = result["workspace"]
        assert ws.get("recent_files") == []


# ---------------------------------------------------------------------------
# P0-2: ToolMediator Enforcement in EveAgentAdapter
# ---------------------------------------------------------------------------

class TestToolMediatorEnforcement:
    """EveAgentAdapter must route tool execution through ToolMediator."""

    def test_adapter_uses_tool_mediator(self):
        from aios.agent.adapter import EveAgentAdapter
        from aios.mediation.tools import ToolMediator

        class FakeRouter:
            pass
        class FakePM:
            pass
        class FakeHM:
            pass

        mediator = ToolMediator()
        adapter = EveAgentAdapter(
            smart_router=FakeRouter(),
            provider_manager=FakePM(),
            health_monitor=FakeHM(),
            tool_mediator=mediator,
        )
        assert adapter._tool_mediator is mediator

    @pytest.mark.asyncio
    async def test_execute_tool_through_mediator(self):
        from aios.agent.adapter import EveAgentAdapter
        from aios.mediation.tools import ToolMediator, ToolCallRequest, ToolCallResult

        class FakeToolMgr:
            async def execute(self, name, params):
                return {"success": True, "result": f"result-{name}"}

        class FakeRouter:
            pass
        class FakePM:
            pass
        class FakeHM:
            pass

        mediator = ToolMediator(tool_manager=FakeToolMgr())
        adapter = EveAgentAdapter(
            smart_router=FakeRouter(),
            provider_manager=FakePM(),
            health_monitor=FakeHM(),
            tool_mediator=mediator,
        )
        result = await adapter.execute_tool("test_tool", {"arg": 1})
        assert result == {"success": True, "result": "result-test_tool"}

    @pytest.mark.asyncio
    async def test_execute_tool_failure_returns_error(self):
        from aios.agent.adapter import EveAgentAdapter
        from aios.mediation.tools import ToolMediator

        class FakeToolMgr:
            async def execute(self, name, params):
                return {"success": False, "error": "tool failed"}

        class FakeRouter:
            pass
        class FakePM:
            pass
        class FakeHM:
            pass

        mediator = ToolMediator(tool_manager=FakeToolMgr())
        adapter = EveAgentAdapter(
            smart_router=FakeRouter(),
            provider_manager=FakePM(),
            health_monitor=FakeHM(),
            tool_mediator=mediator,
        )
        result = await adapter.execute_tool("failing_tool", {})
        assert result == {"success": False, "error": "tool failed"}


# ---------------------------------------------------------------------------
# P0-3: LLM Tool-Calling Loop
# ---------------------------------------------------------------------------

class TestToolCallingLoop:
    """ConversationManager._run_tool_loop executes tools and re-queries."""

    @pytest.mark.asyncio
    async def test_no_tool_calls_returns_content(self):
        from aios.conversation.manager import ConversationManager

        class FakeRouter:
            async def route(self, req, **kwargs):
                return MagicMock(content="Hello!", tool_calls=[], tokens_total=10)

        mgr = ConversationManager(ai_router=FakeRouter())
        conv = MagicMock()
        conv.max_tokens = 100
        conv.temperature = 0.7
        conv.provider_id = None
        conv.model_id = None
        conv.routing_policy = None

        content, tokens = await mgr._run_tool_loop("conv-1", [{"role": "user", "content": "hi"}], conv)
        assert content == "Hello!"
        assert tokens == 10

    @pytest.mark.asyncio
    async def test_tool_calls_execute_and_requery(self):
        from aios.conversation.manager import ConversationManager
        from aios.mediation.tools import ToolMediator, ToolCallResult

        call_count = 0

        class FakeRouter:
            async def route(self, req, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return MagicMock(
                        content="",
                        tool_calls=[{"id": "t1", "type": "function", "function": {"name": "test_tool", "arguments": {"x": 1}}}],
                        tokens_total=5,
                    )
                return MagicMock(content="Done after tool", tool_calls=[], tokens_total=5)

        class FakeToolMgr:
            async def execute(self, name, params):
                return {"result": "tool output"}

        mediator = ToolMediator(tool_manager=FakeToolMgr())
        mgr = ConversationManager(ai_router=FakeRouter(), tool_mediator=mediator)
        conv = MagicMock()
        conv.max_tokens = 100
        conv.temperature = 0.7
        conv.provider_id = None
        conv.model_id = None
        conv.routing_policy = None

        content, tokens = await mgr._run_tool_loop("conv-1", [{"role": "user", "content": "hi"}], conv)
        assert content == "Done after tool"
        assert call_count == 2
        # Tool result should be in the conversation messages
        msgs = mgr._messages.get("conv-1", [])
        tool_msgs = [m for m in msgs if m.tool_results]
        assert len(tool_msgs) == 1

    @pytest.mark.asyncio
    async def test_tool_loop_respects_max_iterations(self):
        from aios.conversation.manager import ConversationManager

        call_count = 0

        class FakeRouter:
            async def route(self, req, **kwargs):
                nonlocal call_count
                call_count += 1
                return MagicMock(
                    content="",
                    tool_calls=[{"id": "t1", "type": "function", "function": {"name": "loop_tool", "arguments": "{}"}}],
                    tokens_total=1,
                )

        class FakeToolMed:
            async def execute(self, request):
                from aios.mediation.tools import ToolCallResult
                return ToolCallResult(success=True, tool_id=request.tool_id, data="ok")

        mgr = ConversationManager(ai_router=FakeRouter(), tool_mediator=FakeToolMed())
        conv = MagicMock()
        conv.max_tokens = 100
        conv.temperature = 0.7
        conv.provider_id = None
        conv.model_id = None
        conv.routing_policy = None

        content, tokens = await mgr._run_tool_loop(
            "conv-1", [{"role": "user", "content": "loop"}], conv, max_iterations=3,
        )
        assert call_count == 3  # stopped at max
