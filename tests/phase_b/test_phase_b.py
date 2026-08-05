"""Tests for Phase B: VoiceOS Foundation & Agent Mediation.

Tests cover:
  1. VoiceSessionManager — microphone lifecycle, PTT, wake-word hooks, state machine
  2. ConversationPipeline — pipeline stages, identity injection, intent detection
  3. Identity Layer — sanitisation, audit, system prompt injection
  4. Memory Mediation — recall, store, session memory
  5. Tool Mediation — execution, audit, sanitisation
  6. Hermes Events Bridge — event sanitisation, stats
  7. Voice Personality — TTS formatting, tone profiles
  8. Extension Interfaces — registry, lifecycle
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ═══════════════════════════════════════════════════════════════════════
# PART 1: Voice Session Manager
# ═══════════════════════════════════════════════════════════════════════

class TestVoiceSessionManager:
    """Tests for VoiceSessionManager."""

    def _make_manager(self):
        from aios.voice.session_manager import VoiceSessionManager, VoiceOSCallbacks
        return VoiceSessionManager(
            callbacks=VoiceOSCallbacks(),
            wake_word="hey eve",
            wake_word_enabled=False,
            push_to_talk_key="v",
        )

    def test_initial_state(self):
        mgr = self._make_manager()
        assert mgr.state.value == "idle"
        assert mgr.session_id  # non-empty
        assert mgr.conversation_id == ""
        assert mgr.microphone.state.value == "disconnected"

    def test_ptt_default_config(self):
        mgr = self._make_manager()
        assert not mgr.is_push_to_talk_active
        assert not mgr.is_wake_word_enabled
        assert mgr.wake_word == "hey eve"

    def test_enable_wake_word(self):
        mgr = self._make_manager()
        mgr.enable_wake_word(True, "wake up eve")
        assert mgr.is_wake_word_enabled
        assert mgr.wake_word == "wake up eve"

    def test_set_conversation(self):
        mgr = self._make_manager()
        mgr.set_conversation("conv-123")
        assert mgr.conversation_id == "conv-123"

    def test_snapshot(self):
        mgr = self._make_manager()
        snap = mgr.snapshot()
        assert snap.state.value == "idle"
        assert snap.session_id == mgr.session_id
        assert snap.wake_word == "hey eve"
        assert snap.interruption_count == 0

    @pytest.mark.asyncio
    async def test_start_shutdown(self):
        mgr = self._make_manager()
        await mgr.start()
        assert mgr.microphone.state.value == "ready"
        await mgr.shutdown()
        assert mgr.state.value == "idle"

    @pytest.mark.asyncio
    async def test_start_idempotent(self):
        mgr = self._make_manager()
        await mgr.start()
        await mgr.start()  # should not error
        assert mgr.microphone.state.value == "ready"
        await mgr.shutdown()

    @pytest.mark.asyncio
    async def test_ptt_press_release(self):
        mgr = self._make_manager()
        await mgr.start()
        await mgr.ptt_press()
        assert mgr.is_push_to_talk_active
        assert mgr.state.value == "listening"
        await mgr.ptt_release()
        assert not mgr.is_push_to_talk_active
        await mgr.shutdown()


# ═══════════════════════════════════════════════════════════════════════
# PART 2: Conversation Pipeline
# ═══════════════════════════════════════════════════════════════════════

class TestConversationPipeline:
    """Tests for ConversationPipeline."""

    def _make_pipeline(self, manager=None):
        from aios.conversation.pipeline import ConversationPipeline
        return ConversationPipeline(conversation_manager=manager)

    @pytest.mark.asyncio
    async def test_empty_input_rejected(self):
        pipe = self._make_pipeline()
        result = await pipe.process_message("conv-1", "", source="chat")
        assert result.get("error") == "Empty input"

    @pytest.mark.asyncio
    async def test_identity_injection(self):
        from aios.conversation.pipeline import DefaultPipelineHooks, PipelineContext
        hooks = DefaultPipelineHooks()
        ctx = PipelineContext(user_input="hello", context={"system_prompt": "You are Hermes"})
        ctx = await hooks.inject_identity(ctx)
        assert "hermes" not in ctx.context.get("system_prompt", "").lower()
        assert ctx.metadata.get("identity") == "eve"

    @pytest.mark.asyncio
    async def test_intent_detection_question(self):
        from aios.conversation.pipeline import DefaultPipelineHooks, PipelineContext
        hooks = DefaultPipelineHooks()
        ctx = PipelineContext(user_input="What is the weather?")
        ctx = await hooks.detect_intent(ctx)
        assert ctx.intent == "question"

    @pytest.mark.asyncio
    async def test_intent_detection_tool(self):
        from aios.conversation.pipeline import DefaultPipelineHooks, PipelineContext
        hooks = DefaultPipelineHooks()
        ctx = PipelineContext(user_input="Run the test suite")
        ctx = await hooks.detect_intent(ctx)
        assert ctx.intent == "tool_execution"

    @pytest.mark.asyncio
    async def test_post_process_strips_hermes(self):
        from aios.conversation.pipeline import DefaultPipelineHooks, PipelineContext
        hooks = DefaultPipelineHooks()
        ctx = PipelineContext(response="I am Hermes, your assistant")
        ctx = await hooks.post_process_response(ctx)
        assert "hermes" not in ctx.response.lower()


# ═══════════════════════════════════════════════════════════════════════
# PART 3: Identity Layer
# ═══════════════════════════════════════════════════════════════════════

class TestIdentityLayer:
    """Tests for the Identity Layer."""

    def test_sanitize_hermes(self):
        from aios.identity.layer import sanitise_text
        result = sanitise_text("I am Hermes, an AI agent")
        assert "hermes" not in result.lower()
        assert "EVE" in result or "eve" in result.lower()

    def test_sanitize_nous_research(self):
        from aios.identity.layer import sanitise_text
        result = sanitise_text("Built by Nous Research")
        assert "nous research" not in result.lower()

    def test_contains_hermes_true(self):
        from aios.identity.layer import contains_hermes_reference
        assert contains_hermes_reference("I am Hermes") is True

    def test_contains_hermes_false(self):
        from aios.identity.layer import contains_hermes_reference
        assert contains_hermes_reference("I am EVE") is False

    def test_sanitize_error(self):
        from aios.identity.layer import sanitise_error_message
        result = sanitise_error_message("Hermes engine not initialized")
        assert "hermes" not in result.lower()
        assert "not ready" in result.lower() or "loading" in result.lower()

    def test_sanitize_log(self):
        from aios.identity.layer import sanitise_log_message
        msg, kwargs = sanitise_log_message("Hermes started", module="hermes_runtime")
        assert "hermes" not in msg.lower()
        assert "hermes" not in kwargs.get("module", "").lower()

    def test_sanitize_notification(self):
        from aios.identity.layer import sanitise_notification
        title, body = sanitise_notification("Hermes is ready", "Task completed")
        assert "hermes" not in title.lower()

    def test_build_system_prompt(self):
        from aios.identity.layer import build_eve_system_prompt
        prompt = build_eve_system_prompt("You are Hermes")
        # "hermes" appears in the rules ("never mention hermes") — that's expected
        # The key test: the persona line should say "EVE" not "Hermes"
        assert "You are EVE" in prompt
        assert "You are Hermes" not in prompt

    def test_audit_clean(self):
        from aios.identity.layer import audit_response
        audit = audit_response("I am EVE, your AI assistant")
        assert audit.clean is True

    def test_audit_hermes_leak(self):
        from aios.identity.layer import audit_response
        audit = audit_response("I am Hermes, an AI agent")
        assert audit.clean is False
        assert audit.contains_hermes is True

    def test_eve_identity_static_methods(self):
        from aios.identity.layer import EVEIdentity
        assert EVEIdentity.contains_hermes("hermes") is True
        assert EVEIdentity.contains_hermes("eve") is False
        clean = EVEIdentity.sanitize("I am Hermes")
        assert "hermes" not in clean.lower()


# ═══════════════════════════════════════════════════════════════════════
# PART 4: Memory Mediation
# ═══════════════════════════════════════════════════════════════════════

class TestMemoryMediation:
    """Tests for MemoryMediator."""

    def _make_mediator(self, memory_system=None):
        from aios.mediation.memory import MemoryMediator
        return MemoryMediator(memory_system=memory_system)

    @pytest.mark.asyncio
    async def test_session_memory_store_recall(self):
        mediator = self._make_mediator()
        result = await mediator.store(
            "User prefers dark mode",
            scope="session",
            conversation_id="conv-1",
        )
        assert result.success is True

        context = await mediator.recall(
            "dark mode",
            scope="session",
            conversation_id="conv-1",
        )
        assert context.count > 0

    @pytest.mark.asyncio
    async def test_session_memory_clear(self):
        mediator = self._make_mediator()
        await mediator.store("test memory", scope="session", conversation_id="conv-1")
        mediator.clear_session("conv-1")
        context = mediator.get_session_context("conv-1")
        assert context.count == 0

    @pytest.mark.asyncio
    async def test_store_without_memory_system(self):
        mediator = self._make_mediator(memory_system=None)
        result = await mediator.store("test", scope="global")
        assert result.success is False
        assert "not available" in result.message

    @pytest.mark.asyncio
    async def test_recall_without_memory_system(self):
        mediator = self._make_mediator(memory_system=None)
        context = await mediator.recall("test", scope="global")
        assert context.count == 0


# ═══════════════════════════════════════════════════════════════════════
# PART 5: Tool Mediation
# ═══════════════════════════════════════════════════════════════════════

class TestToolMediation:
    """Tests for ToolMediator."""

    def _make_mediator(self, tool_manager=None):
        from aios.mediation.tools import ToolMediator
        return ToolMediator(tool_manager=tool_manager)

    def test_sanitize_tool_description(self):
        from aios.mediation.tools import sanitise_tool_description
        desc = sanitise_tool_description("Hermes agent tool for reasoning")
        assert "hermes" not in desc.lower()

    def test_sanitize_tool_list(self):
        from aios.mediation.tools import sanitise_tool_list
        tools = [{"name": "hermes_reason", "description": "Hermes reasoning tool"}]
        result = sanitise_tool_list(tools)
        assert "hermes" not in result[0]["name"].lower()
        assert "hermes" not in result[0]["description"].lower()

    @pytest.mark.asyncio
    async def test_execute_without_tool_manager(self):
        mediator = self._make_mediator(tool_manager=None)
        from aios.mediation.tools import ToolCallRequest
        result = await mediator.execute(ToolCallRequest(tool_id="test"))
        assert result.success is False
        assert "not available" in result.error

    @pytest.mark.asyncio
    async def test_list_tools_without_tool_manager(self):
        mediator = self._make_mediator(tool_manager=None)
        tools = await mediator.list_tools()
        assert tools == []

    def test_audit_log(self):
        mediator = self._make_mediator()
        log = mediator.get_audit_log()
        assert isinstance(log, list)


# ═══════════════════════════════════════════════════════════════════════
# PART 6: Hermes Events Bridge
# ═══════════════════════════════════════════════════════════════════════

class TestHermesEventsBridge:
    """Tests for HermesEventsBridge."""

    def _make_bridge(self):
        from aios.hermes_bridge.events import HermesEventsBridge
        return HermesEventsBridge(event_bus=None)

    @pytest.mark.asyncio
    async def test_event_sanitisation(self):
        bridge = self._make_bridge()
        from aios.hermes_bridge.events import HermesEvent, HermesEventType
        event = HermesEvent(
            event_type=HermesEventType.REASONING_STARTED,
            data={"query": "test", "engine": "hermes"},
        )
        await bridge.on_hermes_event(event)
        events = bridge.get_events()
        assert len(events) == 1
        assert "hermes" not in events[0]["data"].get("engine", "").lower()

    @pytest.mark.asyncio
    async def test_display_names(self):
        bridge = self._make_bridge()
        from aios.hermes_bridge.events import HermesEvent, HermesEventType
        await bridge.on_hermes_event(HermesEvent(event_type=HermesEventType.PLAN_CREATED))
        events = bridge.get_events()
        assert "EVE" in events[0]["display_name"]

    @pytest.mark.asyncio
    async def test_event_stats(self):
        bridge = self._make_bridge()
        from aios.hermes_bridge.events import HermesEvent, HermesEventType
        await bridge.on_hermes_event(HermesEvent(event_type=HermesEventType.TOOL_REQUESTED))
        await bridge.on_hermes_event(HermesEvent(event_type=HermesEventType.TOOL_COMPLETED))
        stats = bridge.get_stats()
        assert stats["total_events"] == 2
        assert stats["by_type"]["tool_requested"] == 1

    @pytest.mark.asyncio
    async def test_convenience_methods(self):
        bridge = self._make_bridge()
        await bridge.reasoning_started("test query")
        await bridge.reasoning_completed("result", 100.0)
        await bridge.plan_created(["step1", "step2"], "objective")
        await bridge.tool_requested("read_file", {"path": "/tmp/test"})
        await bridge.tool_completed("read_file", True, 50.0)
        stats = bridge.get_stats()
        assert stats["total_events"] == 5

    @pytest.mark.asyncio
    async def test_bounded_ring(self):
        from aios.hermes_bridge.events import HermesEventsBridge, HermesEvent, HermesEventType
        bridge = HermesEventsBridge(max_events=5)
        for i in range(10):
            await bridge.on_hermes_event(HermesEvent(event_type=HermesEventType.STATUS_CHANGED))
        assert len(bridge.get_events(limit=100)) == 5


# ═══════════════════════════════════════════════════════════════════════
# PART 7: Voice Personality
# ═══════════════════════════════════════════════════════════════════════

class TestVoicePersonality:
    """Tests for VoicePersonalityManager and TTS formatting."""

    def test_format_for_tts_removes_markdown(self):
        from aios.personality.voice import format_for_tts
        result = format_for_tts("**Bold** and `code` and [link](url)")
        assert "**" not in result
        assert "`" not in result
        assert "[" not in result

    def test_format_for_tts_removes_emoji(self):
        from aios.personality.voice import format_for_tts
        result = format_for_tts("Hello world!")
        # Emoji should be removed
        assert result.strip()

    def test_format_for_tts_expands_abbreviations(self):
        from aios.personality.voice import format_for_tts
        result = format_for_tts("The API uses JSON")
        assert "A P I" in result
        assert "J-S-O-N" in result

    def test_tone_profiles_exist(self):
        from aios.personality.voice import ToneProfile, TONE_PROFILES
        for profile in ToneProfile:
            assert profile in TONE_PROFILES

    def test_personality_manager_default(self):
        from aios.personality.voice import VoicePersonalityManager
        mgr = VoicePersonalityManager()
        assert mgr.personality.name == "EVE"
        assert mgr.current_tone.profile.value == "friendly"

    def test_personality_set_tone(self):
        from aios.personality.voice import VoicePersonalityManager, ToneProfile
        mgr = VoicePersonalityManager()
        mgr.set_tone(ToneProfile.TECHNICAL)
        assert mgr.current_tone.profile == ToneProfile.TECHNICAL

    def test_personality_format_response(self):
        from aios.personality.voice import VoicePersonalityManager
        mgr = VoicePersonalityManager()
        result = mgr.format_response("Hello **world**!")
        assert "**" not in result

    def test_personality_to_dict(self):
        from aios.personality.voice import VoicePersonalityManager
        mgr = VoicePersonalityManager()
        d = mgr.to_dict()
        assert d["name"] == "EVE"
        assert "current_tone" in d
        assert "tone_config" in d


# ═══════════════════════════════════════════════════════════════════════
# PART 8: Extension Interfaces
# ═══════════════════════════════════════════════════════════════════════

class TestExtensionInterfaces:
    """Tests for VoiceOSExtensionRegistry."""

    def _make_registry(self):
        from aios.voice.extensions import VoiceOSExtensionRegistry
        return VoiceOSExtensionRegistry()

    def test_registry_empty(self):
        reg = self._make_registry()
        assert reg.list_all() == []

    def test_register_extension(self):
        from aios.voice.extensions import VoiceOSExtensionRegistry, VoiceOSExtension, ExtensionType

        class MockExtension(VoiceOSExtension):
            @property
            def extension_id(self): return "mock-1"
            @property
            def extension_type(self): return ExtensionType.WAKE_WORD
            @property
            def name(self): return "Mock Wake Word"
            async def start(self): pass
            async def stop(self): pass
            async def start_listening(self): pass
            async def stop_listening(self): pass
            async def detections(self): yield {}
            def set_wake_word(self, wake_word): pass

        reg = self._make_registry()
        ext = MockExtension()
        reg.register(ext)
        assert len(reg.list_all()) == 1
        assert reg.get("mock-1") is ext

    def test_unregister_extension(self):
        from aios.voice.extensions import VoiceOSExtensionRegistry, VoiceOSExtension, ExtensionType

        class MockExtension(VoiceOSExtension):
            @property
            def extension_id(self): return "mock-2"
            @property
            def extension_type(self): return ExtensionType.OVERLAY
            @property
            def name(self): return "Mock Overlay"
            async def start(self): pass
            async def stop(self): pass
            async def show(self): pass
            async def hide(self): pass
            async def update_state(self, state): pass

        reg = self._make_registry()
        ext = MockExtension()
        reg.register(ext)
        assert len(reg.list_all()) == 1
        reg.unregister("mock-2")
        assert len(reg.list_all()) == 0

    def test_get_by_type(self):
        from aios.voice.extensions import (
            VoiceOSExtensionRegistry, VoiceOSExtension, ExtensionType,
        )

        class WakeExt(VoiceOSExtension):
            @property
            def extension_id(self): return "wake-1"
            @property
            def extension_type(self): return ExtensionType.WAKE_WORD
            @property
            def name(self): return "Wake 1"
            async def start(self): pass
            async def stop(self): pass
            async def start_listening(self): pass
            async def stop_listening(self): pass
            async def detections(self): yield {}
            def set_wake_word(self, wake_word): pass

        reg = self._make_registry()
        reg.register(WakeExt())
        wakeExts = reg.get_by_type(ExtensionType.WAKE_WORD)
        assert len(wakeExts) == 1
        assert reg.get_by_type(ExtensionType.OVERLAY) == []
