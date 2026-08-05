"""Tests for Phase C: Context Engine (AI Operating System Kernel).

Covers:
  1. ExecutionContext creation and serialization
  2. Context Provider registration and lifecycle
  3. Context Engine aggregation
  4. Incremental updates
  5. Context versioning
  6. Context cache
  7. Event integration
  8. Context policies (privacy)
  9. Backward compatibility
 10. Performance
"""

import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock


# ═══════════════════════════════════════════════════════════════════════
# PART 1: ExecutionContext
# ═══════════════════════════════════════════════════════════════════════

class TestExecutionContext:
    def test_create_default(self):
        from aios.core.context.models import ExecutionContext
        ctx = ExecutionContext()
        assert ctx.context_id
        assert ctx.version == 0
        assert ctx.timestamp > 0

    def test_to_dict(self):
        from aios.core.context.models import ExecutionContext
        ctx = ExecutionContext()
        d = ctx.to_dict()
        assert "context_id" in d
        assert "window" in d
        assert "clipboard" in d
        assert "workspace" in d
        assert "git" in d
        assert "browser" in d
        assert "voice" in d
        assert "memory" in d
        assert "provider_health" in d

    def test_compute_hash(self):
        from aios.core.context.models import ExecutionContext
        ctx1 = ExecutionContext()
        ctx2 = ExecutionContext()
        # Same structure should produce same hash (ignoring id/timestamp)
        # Different instances will have different ids, so different hashes
        assert ctx1.compute_hash() != ctx2.compute_hash()

    def test_diff_no_previous(self):
        from aios.core.context.models import ExecutionContext
        ctx = ExecutionContext()
        changes = ctx.diff(None)
        assert len(changes) > 0
        assert "window" in changes

    def test_diff_no_changes(self):
        from aios.core.context.models import ExecutionContext
        ctx1 = ExecutionContext()
        ctx2 = ExecutionContext()
        # Copy window state
        ctx2.window = ctx1.window
        ctx2.clipboard = ctx1.clipboard
        ctx2.workspace = ctx1.workspace
        ctx2.git = ctx1.git
        ctx2.browser = ctx1.browser
        ctx2.desktop = ctx1.desktop
        ctx2.voice = ctx1.voice
        ctx2.memory = ctx1.memory
        ctx2.provider_health = ctx1.provider_health
        ctx2.calendar = ctx1.calendar
        ctx2.selection = ctx1.selection
        ctx2.application = ctx1.application
        ctx2.tools = ctx1.tools
        ctx2.notifications = ctx1.notifications
        changes = ctx1.diff(ctx2)
        assert changes == []

    def test_backward_compatible_properties(self):
        from aios.core.context.models import ExecutionContext, WindowContext, ActivityType
        ctx = ExecutionContext()
        ctx.window = WindowContext(active_app="VSCode", active_window="test.py", active_file="/test.py", activity=ActivityType.CODING)
        assert ctx.active_app == "VSCode"
        assert ctx.active_window == "test.py"
        assert ctx.active_file == "/test.py"
        assert ctx.activity == ActivityType.CODING


# ═══════════════════════════════════════════════════════════════════════
# PART 2: Context Providers
# ═══════════════════════════════════════════════════════════════════════

class TestContextProviders:
    def test_all_providers_instantiate(self):
        from aios.core.context.providers import (
            ClipboardProvider, WindowProvider, WorkspaceProvider,
            GitProvider, BrowserProvider, DesktopProvider,
            VoiceProvider, MemoryProvider, ProviderHealthProvider,
            CalendarProvider, SelectionProvider, ApplicationProvider,
            ToolProvider, NotificationProvider,
        )
        providers = [
            ClipboardProvider(), WindowProvider(), WorkspaceProvider(),
            GitProvider(), BrowserProvider(), DesktopProvider(),
            VoiceProvider(), MemoryProvider(), ProviderHealthProvider(),
            CalendarProvider(), SelectionProvider(), ApplicationProvider(),
            ToolProvider(), NotificationProvider(),
        ]
        assert len(providers) == 14
        for p in providers:
            assert p.provider_id
            assert p.display_name
            assert p.scope

    @pytest.mark.asyncio
    async def test_clipboard_provider(self):
        from aios.core.context.providers import ClipboardProvider
        p = ClipboardProvider()
        result = await p.collect()
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_workspace_provider(self):
        from aios.core.context.providers import WorkspaceProvider
        p = WorkspaceProvider()
        p.set_workspace("/test/workspace")
        p.add_recent_file("/test/file.py")
        result = await p.collect()
        assert "workspace" in result

    @pytest.mark.asyncio
    async def test_voice_provider_events(self):
        from aios.core.context.providers import VoiceProvider
        p = VoiceProvider()
        await p.on_event("voice:state:change", {"state": "listening"})
        result = await p.collect()
        assert result["voice"]["state"] == "listening"

    @pytest.mark.asyncio
    async def test_selection_provider(self):
        from aios.core.context.providers import SelectionProvider
        p = SelectionProvider()
        p.update(text="selected code", source_app="VSCode")
        result = await p.collect()
        assert result["selection"]["has_selection"] is True

    @pytest.mark.asyncio
    async def test_notification_provider(self):
        from aios.core.context.providers import NotificationProvider
        p = NotificationProvider()
        p.add_notification({"title": "Test", "body": "Hello"})
        result = await p.collect()
        assert result["notifications"]["unread_count"] == 1


# ═══════════════════════════════════════════════════════════════════════
# PART 3: Context Engine
# ═══════════════════════════════════════════════════════════════════════

class TestContextEngine:
    def _make_engine(self):
        from aios.core.context.engine import ContextEngine
        return ContextEngine(poll_interval=100)  # large interval to prevent auto-poll

    def test_create_engine(self):
        engine = self._make_engine()
        assert engine.get_version() == 0

    def test_register_provider(self):
        from aios.core.context.providers import WorkspaceProvider
        engine = self._make_engine()
        p = WorkspaceProvider()
        engine.register_provider(p)
        assert engine.get_provider("workspace") is p
        assert len(engine.list_providers()) == 1

    def test_unregister_provider(self):
        from aios.core.context.providers import WorkspaceProvider
        engine = self._make_engine()
        p = WorkspaceProvider()
        engine.register_provider(p)
        engine.unregister_provider("workspace")
        assert engine.get_provider("workspace") is None

    @pytest.mark.asyncio
    async def test_collect(self):
        from aios.core.context.providers import WorkspaceProvider, DesktopProvider
        engine = self._make_engine()
        engine.register_provider(WorkspaceProvider())
        engine.register_provider(DesktopProvider())
        ctx = await engine.collect()
        assert ctx.version == 1
        assert ctx.workspace is not None
        assert ctx.desktop is not None

    @pytest.mark.asyncio
    async def test_version_increments(self):
        from aios.core.context.providers import WorkspaceProvider
        engine = self._make_engine()
        engine.register_provider(WorkspaceProvider())
        ctx1 = await engine.collect()
        ctx2 = await engine.collect()
        assert ctx2.version == ctx1.version + 1

    @pytest.mark.asyncio
    async def test_snapshot(self):
        engine = self._make_engine()
        ctx = await engine.snapshot()
        assert ctx is not None
        assert ctx.version >= 1

    def test_diagnostics(self):
        engine = self._make_engine()
        diag = engine.diagnostics()
        assert "version" in diag
        assert "providers" in diag
        assert "running" in diag


# ═══════════════════════════════════════════════════════════════════════
# PART 4: Incremental Updates
# ═══════════════════════════════════════════════════════════════════════

class TestIncrementalUpdates:
    @pytest.mark.asyncio
    async def test_diff_detects_changes(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.models import ExecutionContext, SelectionContext
        engine = ContextEngine(poll_interval=100)
        ctx1 = ExecutionContext()
        ctx2 = ExecutionContext()
        ctx2.selection = SelectionContext(selected_text="new text", source_app="VSCode")
        changes = ctx2.diff(ctx1)
        assert "selection" in changes

    @pytest.mark.asyncio
    async def test_cache_section(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import WorkspaceProvider
        engine = ContextEngine(poll_interval=100)
        engine.register_provider(WorkspaceProvider())
        await engine.collect()
        cached = engine.get_section_cache("workspace")
        assert cached is not None


# ═══════════════════════════════════════════════════════════════════════
# PART 5: Context Versioning
# ═══════════════════════════════════════════════════════════════════════

class TestContextVersioning:
    @pytest.mark.asyncio
    async def test_version_starts_at_zero(self):
        from aios.core.context.engine import ContextEngine
        engine = ContextEngine(poll_interval=100)
        assert engine.get_version() == 0

    @pytest.mark.asyncio
    async def test_version_increments_on_collect(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import DesktopProvider
        engine = ContextEngine(poll_interval=100)
        engine.register_provider(DesktopProvider())
        await engine.collect()
        assert engine.get_version() == 1
        await engine.collect()
        assert engine.get_version() == 2

    @pytest.mark.asyncio
    async def test_context_has_version(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import DesktopProvider
        engine = ContextEngine(poll_interval=100)
        engine.register_provider(DesktopProvider())
        ctx = await engine.collect()
        assert ctx.version == 1


# ═══════════════════════════════════════════════════════════════════════
# PART 6: Context Cache
# ═══════════════════════════════════════════════════════════════════════

class TestContextCache:
    @pytest.mark.asyncio
    async def test_cache_populated(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import WorkspaceProvider
        engine = ContextEngine(poll_interval=100)
        engine.register_provider(WorkspaceProvider())
        await engine.collect()
        cached = engine.get_section_cache("workspace")
        assert cached is not None

    @pytest.mark.asyncio
    async def test_invalidate_section(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import WorkspaceProvider
        engine = ContextEngine(poll_interval=100)
        engine.register_provider(WorkspaceProvider())
        await engine.collect()
        engine.invalidate_cache("workspace")
        cached = engine.get_section_cache("workspace")
        assert cached is None

    @pytest.mark.asyncio
    async def test_invalidate_all(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import WorkspaceProvider, DesktopProvider
        engine = ContextEngine(poll_interval=100)
        engine.register_provider(WorkspaceProvider())
        engine.register_provider(DesktopProvider())
        await engine.collect()
        engine.invalidate_cache()
        assert engine.get_section_cache("workspace") is None
        assert engine.get_section_cache("desktop") is None


# ═══════════════════════════════════════════════════════════════════════
# PART 7: Event Integration
# ═══════════════════════════════════════════════════════════════════════

class TestEventIntegration:
    @pytest.mark.asyncio
    async def test_subscriber_notification(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import SelectionProvider
        engine = ContextEngine(poll_interval=100)
        engine.register_provider(SelectionProvider())
        received = []
        def on_change(ctx, changes):
            received.append((ctx, changes))
        engine.subscribe(on_change)
        engine.get_provider("selection").update("text")
        await engine.collect()
        assert len(received) == 1


# ═══════════════════════════════════════════════════════════════════════
# PART 8: Context Policies
# ═══════════════════════════════════════════════════════════════════════

class TestContextPolicies:
    def test_clean_content_allowed(self):
        from aios.core.context.policy import ContextPolicy
        from aios.core.context.models import ExecutionContext, ClipboardContext
        policy = ContextPolicy()
        ctx = ExecutionContext()
        ctx.clipboard = ClipboardContext(text="Hello world", has_content=True)
        result = policy.enforce(ctx)
        assert result.clipboard.text == "Hello world"

    def test_api_key_redacted(self):
        from aios.core.context.policy import ContextPolicy
        from aios.core.context.models import ExecutionContext, ClipboardContext
        policy = ContextPolicy()
        ctx = ExecutionContext()
        ctx.clipboard = ClipboardContext(text="api_key=sk-abc123def456ghi789", has_content=True)
        result = policy.enforce(ctx)
        assert "REDACTED" in result.clipboard.text

    def test_password_manager_redacted(self):
        from aios.core.context.policy import ContextPolicy
        from aios.core.context.models import ExecutionContext, WindowContext
        policy = ContextPolicy()
        ctx = ExecutionContext()
        ctx.window = WindowContext(active_app="1Password")
        result = policy.enforce(ctx)
        assert "REDACTED" in result.window.active_app

    def test_incognito_browser_redacted(self):
        from aios.core.context.policy import ContextPolicy
        from aios.core.context.models import ExecutionContext, BrowserContext
        policy = ContextPolicy()
        ctx = ExecutionContext()
        ctx.browser = BrowserContext(active_tab_title="Google - Incognito")
        result = policy.enforce(ctx)
        assert "Private" in result.browser.active_tab_title

    def test_evaluate_reports_redaction(self):
        from aios.core.context.policy import ContextPolicy
        from aios.core.context.models import ExecutionContext, ClipboardContext
        policy = ContextPolicy()
        ctx = ExecutionContext()
        ctx.clipboard = ClipboardContext(text="api_key=sk-abc123def456ghi789", has_content=True)
        decision = policy.evaluate(ctx)
        assert decision.redacted is True
        assert "clipboard.text" in decision.redacted_fields


# ═══════════════════════════════════════════════════════════════════════
# PART 9: Backward Compatibility
# ═══════════════════════════════════════════════════════════════════════

class TestBackwardCompatibility:
    def test_context_alias(self):
        from aios.core.context_engine import Context, ExecutionContext
        assert Context is ExecutionContext

    @pytest.mark.asyncio
    async def test_get_active_app(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import WindowProvider
        engine = ContextEngine(poll_interval=100)
        # No window provider — should return empty
        app = await engine.get_active_app()
        assert app == ""

    @pytest.mark.asyncio
    async def test_detect_project(self):
        from aios.core.context.engine import ContextEngine
        engine = ContextEngine(poll_interval=100)
        project = await engine.detect_project()
        assert project is None

    @pytest.mark.asyncio
    async def test_get_recent_activity(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import DesktopProvider
        engine = ContextEngine(poll_interval=100)
        engine.register_provider(DesktopProvider())
        await engine.collect()
        recent = await engine.get_recent_activity(minutes=5)
        assert len(recent) >= 1


# ═══════════════════════════════════════════════════════════════════════
# PART 10: Performance
# ═══════════════════════════════════════════════════════════════════════

class TestPerformance:
    @pytest.mark.asyncio
    async def test_collect_under_100ms(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import (
            WorkspaceProvider, DesktopProvider, VoiceProvider,
            SelectionProvider, NotificationProvider,
        )
        engine = ContextEngine(poll_interval=100)
        engine.register_provider(WorkspaceProvider())
        engine.register_provider(DesktopProvider())
        engine.register_provider(VoiceProvider())
        engine.register_provider(SelectionProvider())
        engine.register_provider(NotificationProvider())
        start = time.monotonic()
        await engine.collect()
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 100, f"Context collection took {elapsed:.1f}ms (target: <100ms)"

    @pytest.mark.asyncio
    async def test_diff_under_1ms(self):
        from aios.core.context.engine import ContextEngine
        from aios.core.context.providers import WorkspaceProvider
        engine = ContextEngine(poll_interval=100)
        engine.register_provider(WorkspaceProvider())
        ctx1 = await engine.collect()
        ctx2 = await engine.collect()
        start = time.monotonic()
        ctx2.diff(ctx1)
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 1, f"Diff took {elapsed:.3f}ms (target: <1ms)"

    @pytest.mark.asyncio
    async def test_hash_under_5ms(self):
        from aios.core.context.models import ExecutionContext
        ctx = ExecutionContext()
        start = time.monotonic()
        ctx.compute_hash()
        elapsed = (time.monotonic() - start) * 1000
        assert elapsed < 5, f"Hash took {elapsed:.2f}ms (target: <5ms)"
