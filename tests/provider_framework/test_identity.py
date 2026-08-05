"""Tests for Voice Identity System (Sprint D8)."""

import time
import json
import threading
import tempfile
import os
import pytest
from unittest.mock import MagicMock

from aios.voice.identity.models import (
    VoiceProfile, PersonalityType, SpeakingStyle, SpeakingStyleConfig,
    AdaptationContext, IdentityPreferences, IdentitySnapshot,
    PronunciationEntry, CONTEXT_TO_PROFILE_MAP,
)
from aios.voice.identity.events import IdentityEvent, IdentityEventType
from aios.voice.identity.personality import (
    BUILTIN_PROFILES, get_builtin_profile, list_builtin_profiles,
)
from aios.voice.identity.adaptation import (
    ContextAdapter, AdaptationResult, AdaptationReason,
)
from aios.voice.identity.pronunciation import PronunciationDictionary
from aios.voice.identity.preferences import PreferenceManager
from aios.voice.identity.metrics import IdentityMetrics, IdentityMetricsSnapshot
from aios.voice.identity.manager import VoiceIdentityManager


# === Models Tests ===

class TestSpeakingStyleConfig:
    def test_defaults(self):
        s = SpeakingStyleConfig()
        assert s.speech_rate == 1.0
        assert s.pause_duration_ms == 200.0
        assert s.response_length == "medium"
        assert s.technical_wording is False

    def test_to_dict(self):
        s = SpeakingStyleConfig(speech_rate=1.2)
        d = s.to_dict()
        assert d["speech_rate"] == 1.2

    def test_from_dict(self):
        s = SpeakingStyleConfig.from_dict({"speech_rate": 1.3, "pitch_offset": 0.1})
        assert s.speech_rate == 1.3
        assert s.pitch_offset == 0.1

    def test_from_dict_ignores_unknown(self):
        s = SpeakingStyleConfig.from_dict({"speech_rate": 1.0, "unknown_key": 99})
        assert s.speech_rate == 1.0


class TestVoiceProfile:
    def test_creation(self):
        p = VoiceProfile(profile_id="test", name="Test", personality=PersonalityType.FRIENDLY)
        assert p.profile_id == "test"
        assert p.is_builtin is False

    def test_to_dict(self):
        p = VoiceProfile(profile_id="test", name="Test", personality=PersonalityType.FRIENDLY)
        d = p.to_dict()
        assert d["profile_id"] == "test"
        assert d["personality"] == "friendly"
        assert "style" in d


class TestIdentityPreferences:
    def test_defaults(self):
        prefs = IdentityPreferences()
        assert prefs.preferred_voice == "default"
        assert prefs.speech_speed == 1.0
        assert prefs.preferred_profile == "friendly"

    def test_to_dict(self):
        prefs = IdentityPreferences(preferred_voice="nova")
        d = prefs.to_dict()
        assert d["preferred_voice"] == "nova"

    def test_from_dict(self):
        prefs = IdentityPreferences.from_dict({"preferred_voice": "shimmer", "speech_speed": 1.2})
        assert prefs.preferred_voice == "shimmer"
        assert prefs.speech_speed == 1.2


# === Events Tests ===

class TestIdentityEvent:
    def test_creation(self):
        e = IdentityEvent(event_type=IdentityEventType.PROFILE_CHANGED)
        assert e.event_type == IdentityEventType.PROFILE_CHANGED

    def test_all_event_types(self):
        for et in IdentityEventType:
            e = IdentityEvent(event_type=et)
            assert e.event_type == et

    def test_to_dict(self):
        e = IdentityEvent(event_type=IdentityEventType.IDENTITY_LOADED, profile_id="friendly")
        d = e.to_dict()
        assert d["profile_id"] == "friendly"


# === Personality Tests ===

class TestPersonality:
    def test_all_builtin_present(self):
        assert len(BUILTIN_PROFILES) == 8
        for pid in ["professional", "friendly", "technical", "minimal",
                     "companion", "teacher", "creative", "executive"]:
            assert pid in BUILTIN_PROFILES

    def test_get_builtin(self):
        p = get_builtin_profile("friendly")
        assert p.name == "Friendly"
        assert p.is_builtin is True

    def test_get_unknown_raises(self):
        with pytest.raises(ValueError):
            get_builtin_profile("nonexistent")

    def test_list_builtin(self):
        profiles = list_builtin_profiles()
        assert len(profiles) == 8

    def test_all_have_style(self):
        for p in BUILTIN_PROFILES.values():
            assert isinstance(p.style, SpeakingStyleConfig)
            assert p.style.speech_rate > 0

    def test_all_have_phrases(self):
        for p in BUILTIN_PROFILES.values():
            assert len(p.confirmation_phrases) > 0

    def test_professional_is_concise(self):
        p = BUILTIN_PROFILES["professional"]
        assert p.verbosity == 0.5

    def test_minimal_is_brief(self):
        p = BUILTIN_PROFILES["minimal"]
        assert p.verbosity == 0.2
        assert p.style.response_length == "short"

    def test_companion_is_verbose(self):
        p = BUILTIN_PROFILES["companion"]
        assert p.verbosity == 0.8
        assert p.style.filler_usage > 0

    def test_technical_is_technical(self):
        p = BUILTIN_PROFILES["technical"]
        assert p.style.technical_wording is True


# === Adaptation Tests ===

class TestContextAdapter:
    def test_creation(self):
        a = ContextAdapter()
        assert a.current_context == AdaptationContext.GENERAL
        assert a.current_profile_id == "friendly"

    def test_adapt_to_coding(self):
        a = ContextAdapter()
        result = a.adapt(AdaptationContext.CODING)
        assert result.adapted is True
        assert result.new_profile == "technical"
        assert a.current_context == AdaptationContext.CODING

    def test_adapt_to_design(self):
        a = ContextAdapter()
        result = a.adapt(AdaptationContext.DESIGN)
        assert result.new_profile == "creative"

    def test_adapt_to_meeting(self):
        a = ContextAdapter()
        result = a.adapt(AdaptationContext.MEETING)
        assert result.new_profile == "executive"

    def test_adapt_to_teaching(self):
        a = ContextAdapter()
        result = a.adapt(AdaptationContext.TEACHING)
        assert result.new_profile == "teacher"

    def test_adapt_to_quick_command(self):
        a = ContextAdapter()
        result = a.adapt(AdaptationContext.QUICK_COMMAND)
        assert result.new_profile == "minimal"

    def test_same_context_no_adapt(self):
        a = ContextAdapter()
        r1 = a.adapt(AdaptationContext.CODING)
        r2 = a.adapt(AdaptationContext.CODING)
        assert r2.adapted is False

    def test_force_adapt(self):
        a = ContextAdapter()
        a.adapt(AdaptationContext.CODING)
        result = a.adapt(AdaptationContext.CODING, force=True)
        assert result.adapted is True

    def test_disabled_no_adapt(self):
        a = ContextAdapter()
        a.set_enabled(False)
        result = a.adapt(AdaptationContext.CODING)
        assert result.adapted is False

    def test_custom_mapping(self):
        a = ContextAdapter()
        a.set_profile_for_context(AdaptationContext.CODING, "companion")
        result = a.adapt(AdaptationContext.CODING)
        assert result.new_profile == "companion"

    def test_force_profile(self):
        a = ContextAdapter()
        result = a.force_profile("executive")
        assert result.adapted is True
        assert result.new_profile == "executive"
        assert result.reason == AdaptationReason.USER_OVERRIDE

    def test_history_tracking(self):
        a = ContextAdapter()
        a.adapt(AdaptationContext.CODING)
        a.adapt(AdaptationContext.DESIGN)
        assert len(a.get_history()) == 2

    def test_clear_history(self):
        a = ContextAdapter()
        a.adapt(AdaptationContext.CODING)
        a.clear_history()
        assert len(a.get_history()) == 0

    def test_snapshot(self):
        a = ContextAdapter()
        snap = a.snapshot()
        assert "enabled" in snap
        assert "current_context" in snap

    def test_reset(self):
        a = ContextAdapter()
        a.adapt(AdaptationContext.CODING)
        a.reset()
        assert a.current_context == AdaptationContext.GENERAL


# === Pronunciation Tests ===

class TestPronunciationDictionary:
    def test_creation(self):
        d = PronunciationDictionary()
        assert d.count == 0

    def test_add_and_lookup(self):
        d = PronunciationDictionary()
        d.add("TypeScript", "TY-pah-skript")
        assert d.has("TypeScript")
        assert d.lookup("TypeScript").phonetic == "TY-pah-skript"

    def test_case_insensitive(self):
        d = PronunciationDictionary()
        d.add("groq", "GROK")
        assert d.has("Groq")
        assert d.has("GROQ")

    def test_remove(self):
        d = PronunciationDictionary()
        d.add("test", "TEST")
        assert d.remove("test") is True
        assert d.has("test") is False

    def test_remove_nonexistent(self):
        d = PronunciationDictionary()
        assert d.remove("nonexistent") is False

    def test_get_all(self):
        d = PronunciationDictionary()
        d.add("a", "AY")
        d.add("b", "BEE")
        assert len(d.get_all()) == 2

    def test_get_by_category(self):
        d = PronunciationDictionary()
        d.add("typescript", "TY", category="technology")
        d.add("alice", "AH-lis", category="name")
        tech = d.get_by_category("technology")
        assert len(tech) == 1

    def test_get_by_language(self):
        d = PronunciationDictionary()
        d.add("bonjour", "bon-ZHOOR", language="fr")
        fr = d.get_by_language("fr")
        assert len(fr) == 1

    def test_clear(self):
        d = PronunciationDictionary()
        d.add("a", "AY")
        d.clear()
        assert d.count == 0

    def test_export_import_dict(self):
        d = PronunciationDictionary()
        d.add("test", "TEST", category="custom")
        exported = d.export_dict()
        d2 = PronunciationDictionary()
        d2.import_dict(exported)
        assert d2.has("test")

    def test_export_import_json(self):
        d = PronunciationDictionary()
        d.add("test", "TEST")
        json_str = d.export_json()
        d2 = PronunciationDictionary()
        d2.import_json(json_str)
        assert d2.has("test")

    def test_load_defaults(self):
        d = PronunciationDictionary()
        d.load_defaults()
        assert d.count >= 8
        assert d.has("typescript")
        assert d.has("groq")
        assert d.has("gemini")

    def test_snapshot(self):
        d = PronunciationDictionary()
        d.add("test", "TEST", category="tech")
        snap = d.snapshot()
        assert snap["total_entries"] == 1
        assert "tech" in snap["categories"]

    def test_thread_safety(self):
        d = PronunciationDictionary()
        errors = []

        def writer():
            for i in range(20):
                try:
                    d.add(f"word{i}", f"W{i}")
                except Exception as e:
                    errors.append(e)

        def reader():
            for _ in range(20):
                try:
                    d.get_all()
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=writer) for _ in range(3)]
        threads += [threading.Thread(target=reader) for _ in range(3)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert not errors


# === Preferences Tests ===

class TestPreferenceManager:
    def test_creation(self):
        pm = PreferenceManager()
        assert pm.loaded is False

    def test_load_default(self):
        pm = PreferenceManager()
        pm.load()
        assert pm.loaded is True

    def test_load_from_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"preferred_voice": "nova", "speech_speed": 1.3}, f)
            path = f.name
        try:
            pm = PreferenceManager(storage_path=path)
            pm.load()
            assert pm.preferences.preferred_voice == "nova"
            assert pm.preferences.speech_speed == 1.3
        finally:
            os.unlink(path)

    def test_save_to_file(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            pm = PreferenceManager(storage_path=path)
            pm.load()
            pm.set_preferred_voice("shimmer")
            pm.save()
            pm2 = PreferenceManager(storage_path=path)
            pm2.load()
            assert pm2.preferences.preferred_voice == "shimmer"
        finally:
            os.unlink(path)

    def test_update(self):
        pm = PreferenceManager()
        pm.load()
        pm.update(preferred_voice="nova", speech_speed=1.2)
        assert pm.preferences.preferred_voice == "nova"
        assert pm.modified is True

    def test_setters(self):
        pm = PreferenceManager()
        pm.load()
        pm.set_preferred_voice("shimmer")
        pm.set_speech_speed(1.3)
        pm.set_pitch(0.2)
        pm.set_verbosity(0.8)
        pm.set_preferred_profile("technical")
        pm.set_address_user_as("Boss")
        assert pm.preferences.preferred_voice == "shimmer"
        assert pm.preferences.speech_speed == 1.3

    def test_speed_clamped(self):
        pm = PreferenceManager()
        pm.load()
        pm.set_speech_speed(5.0)
        assert pm.preferences.speech_speed == 2.0
        pm.set_speech_speed(0.1)
        assert pm.preferences.speech_speed == 0.5

    def test_reset(self):
        pm = PreferenceManager()
        pm.load()
        pm.set_preferred_voice("nova")
        pm.reset()
        assert pm.preferences.preferred_voice == "default"

    def test_export_import(self):
        pm = PreferenceManager()
        pm.load()
        pm.set_preferred_voice("nova")
        data = pm.export_dict()
        pm2 = PreferenceManager()
        pm2.import_dict(data)
        assert pm2.preferences.preferred_voice == "nova"

    def test_snapshot(self):
        pm = PreferenceManager()
        pm.load()
        snap = pm.snapshot()
        assert "loaded" in snap
        assert "preferences" in snap


# === Metrics Tests ===

class TestIdentityMetrics:
    def test_basics(self):
        m = IdentityMetrics()
        assert m.uptime > 0

    def test_adaptation_recording(self):
        m = IdentityMetrics()
        m.record_adaptation(5.0)
        m.record_adaptation(10.0)
        snap = m.snapshot()
        assert snap.total_adaptations == 2
        assert snap.avg_adaptation_latency_ms == 7.5

    def test_context_switches(self):
        m = IdentityMetrics()
        m.record_context_switch()
        snap = m.snapshot()
        assert snap.context_switches == 1

    def test_profile_changes(self):
        m = IdentityMetrics()
        m.record_profile_change()
        snap = m.snapshot()
        assert snap.profile_changes == 1

    def test_pronunciation_lookups(self):
        m = IdentityMetrics()
        m.record_pronunciation_lookup()
        snap = m.snapshot()
        assert snap.pronunciation_lookups == 1

    def test_preference_updates(self):
        m = IdentityMetrics()
        m.record_preference_update()
        snap = m.snapshot()
        assert snap.preference_updates == 1

    def test_adaptations_today(self):
        m = IdentityMetrics()
        m.record_adaptation(1.0)
        m.record_adaptation(2.0)
        snap = m.snapshot()
        assert snap.adaptations_today == 2

    def test_snapshot_with_params(self):
        m = IdentityMetrics()
        snap = m.snapshot(current_profile="technical", current_context="coding")
        assert snap.current_profile == "technical"
        assert snap.current_context == "coding"

    def test_to_dict(self):
        m = IdentityMetrics()
        snap = m.snapshot()
        d = snap.to_dict()
        assert isinstance(d, dict)

    def test_reset(self):
        m = IdentityMetrics()
        m.record_adaptation(1.0)
        m.record_context_switch()
        m.reset()
        snap = m.snapshot()
        assert snap.total_adaptations == 0


# === Manager Tests ===

class TestVoiceIdentityManager:
    def test_creation(self):
        mgr = VoiceIdentityManager()
        assert mgr.initialized is False

    def test_initialize(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        assert mgr.initialized is True
        assert mgr.active_profile_id == "friendly"

    def test_shutdown(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        mgr.shutdown()
        assert mgr.initialized is False

    def test_list_profiles(self):
        mgr = VoiceIdentityManager()
        profiles = mgr.list_profiles()
        assert len(profiles) == 8

    def test_get_profile(self):
        mgr = VoiceIdentityManager()
        p = mgr.get_profile("technical")
        assert p is not None
        assert p.name == "Technical"

    def test_get_unknown_profile(self):
        mgr = VoiceIdentityManager()
        assert mgr.get_profile("nonexistent") is None

    def test_switch_profile(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        assert mgr.switch_profile("technical") is True
        assert mgr.active_profile_id == "technical"

    def test_switch_unknown_profile(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        assert mgr.switch_profile("nonexistent") is False

    def test_create_profile(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        p = VoiceProfile(profile_id="custom1", name="Custom",
                         personality=PersonalityType.CUSTOM)
        mgr.create_profile(p)
        assert mgr.get_profile("custom1") is not None

    def test_update_profile(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        mgr.create_profile(VoiceProfile(profile_id="c1", name="C1",
                                        personality=PersonalityType.CUSTOM))
        updated = mgr.update_profile("c1", name="Updated C1")
        assert updated.name == "Updated C1"

    def test_update_builtin_rejected(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        assert mgr.update_profile("friendly", name="Hacked") is None

    def test_delete_profile(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        mgr.create_profile(VoiceProfile(profile_id="c1", name="C1",
                                        personality=PersonalityType.CUSTOM))
        assert mgr.delete_profile("c1") is True
        assert mgr.get_profile("c1") is None

    def test_delete_builtin_rejected(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        assert mgr.delete_profile("friendly") is False

    def test_delete_active_rejected(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        mgr.create_profile(VoiceProfile(profile_id="c1", name="C1",
                                        personality=PersonalityType.CUSTOM))
        mgr.switch_profile("c1")
        assert mgr.delete_profile("c1") is False

    def test_duplicate_profile(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        dup = mgr.duplicate_profile("friendly", "friendly2", "Friendly 2")
        assert dup is not None
        assert dup.name == "Friendly 2"
        assert dup.is_builtin is False

    def test_duplicate_nonexistent(self):
        mgr = VoiceIdentityManager()
        assert mgr.duplicate_profile("nonexistent", "x") is None

    def test_adapt_to_context(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        result = mgr.adapt_to_context(AdaptationContext.CODING)
        assert result.adapted is True
        assert mgr.active_profile_id == "technical"

    def test_adapt_to_error(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        result = mgr.adapt_to_error()
        assert result.adapted is True
        assert mgr.active_profile_id == "minimal"

    def test_adapt_to_success(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        result = mgr.adapt_to_success()
        assert result.adapted is True
        assert mgr.active_profile_id == "friendly"

    def test_set_speaking_style(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        style = SpeakingStyleConfig(speech_rate=1.5)
        mgr.set_speaking_style(style)
        assert mgr.get_speaking_style().speech_rate == 1.5

    def test_get_confirmation_phrase(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        phrase = mgr.get_confirmation_phrase()
        assert len(phrase) > 0

    def test_get_greeting(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        g = mgr.get_greeting()
        assert len(g) > 0

    def test_get_farewell(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        f = mgr.get_farewell()
        assert len(f) > 0

    def test_format_response_error(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        result = mgr.format_response("something broke", is_error=True)
        assert "something broke" in result

    def test_format_response_success(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        result = mgr.format_response("task done", is_success=True)
        assert "task done" in result

    def test_format_response_neutral(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        result = mgr.format_response("hello")
        assert result == "hello"

    def test_pronunciation_integration(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        mgr.add_pronunciation("groq", "GROK")
        entry = mgr.lookup_pronunciation("groq")
        assert entry.phonetic == "GROK"

    def test_preferences_integration(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        mgr.update_preferences(preferred_voice="nova")
        assert mgr.preferences.get("preferred_voice") == "nova"

    def test_export_import_profiles(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        mgr.create_profile(VoiceProfile(profile_id="c1", name="C1",
                                        personality=PersonalityType.CUSTOM))
        exported = mgr.export_profiles()
        assert "c1" in exported
        mgr2 = VoiceIdentityManager()
        count = mgr2.import_profiles(exported)
        assert count == 1
        assert mgr2.get_profile("c1") is not None

    def test_event_handlers(self):
        mgr = VoiceIdentityManager()
        events = []
        mgr.on(IdentityEventType.PROFILE_CHANGED, lambda ev: events.append(ev))
        mgr.initialize()
        mgr.switch_profile("technical")
        assert len(events) == 1

    def test_snapshot(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        snap = mgr.snapshot()
        assert snap["initialized"] is True
        assert "active_profile" in snap
        assert "adapter" in snap
        assert "pronunciation" in snap

    def test_reset(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        mgr.switch_profile("technical")
        mgr.reset()
        assert mgr.initialized is False
        assert mgr.active_profile_id == "friendly"

    def test_thread_safety(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        errors = []

        def switcher():
            for i in range(10):
                try:
                    profiles = ["technical", "friendly", "minimal", "creative"]
                    mgr.switch_profile(profiles[i % len(profiles)])
                except Exception as e:
                    errors.append(e)

        def snap():
            for _ in range(10):
                try:
                    mgr.snapshot()
                except Exception as e:
                    errors.append(e)

        threads = [threading.Thread(target=switcher) for _ in range(3)]
        threads += [threading.Thread(target=snap) for _ in range(3)]
        for th in threads:
            th.start()
        for th in threads:
            th.join()
        assert not errors


# === Integration Tests ===

class TestIdentityIntegration:
    def test_full_lifecycle(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()

        assert mgr.active_profile_id == "friendly"
        mgr.adapt_to_context(AdaptationContext.CODING)
        assert mgr.active_profile_id == "technical"
        mgr.adapt_to_context(AdaptationContext.DESIGN)
        assert mgr.active_profile_id == "creative"
        mgr.adapt_to_error()
        assert mgr.active_profile_id == "minimal"
        mgr.adapt_to_success()
        assert mgr.active_profile_id == "friendly"

        mgr.shutdown()

    def test_pronunciation_workflow(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        # "TypeScript" lowercases to "typescript" which is in defaults already
        mgr.add_pronunciation("Swaraj", "SWAH-raj", category="name")
        mgr.add_pronunciation("Kubernetes", "koo-ber-NET-eez", category="technology")
        assert mgr.lookup_pronunciation("Swaraj").phonetic == "SWAH-raj"
        assert mgr.lookup_pronunciation("Kubernetes").phonetic == "koo-ber-NET-eez"
        assert mgr.pronunciation.count == 2 + 10  # 2 custom + 10 defaults

    def test_preferences_persistence(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            path = f.name
        try:
            mgr1 = VoiceIdentityManager(storage_path=path)
            mgr1.initialize()
            mgr1.update_preferences(preferred_voice="nova", speech_speed=1.3)
            mgr1.shutdown()

            mgr2 = VoiceIdentityManager(storage_path=path)
            mgr2.initialize()
            assert mgr2.preferences.get("preferred_voice") == "nova"
            assert mgr2.preferences.get("speech_speed") == 1.3
        finally:
            os.unlink(path)

    def test_context_adaptation_chain(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        mgr.adapt_to_context(AdaptationContext.MEETING)
        assert mgr.active_profile_id == "executive"
        mgr.adapt_to_context(AdaptationContext.TEACHING)
        assert mgr.active_profile_id == "teacher"
        mgr.adapt_to_context(AdaptationContext.QUICK_COMMAND)
        assert mgr.active_profile_id == "minimal"

    def test_profile_customization(self):
        mgr = VoiceIdentityManager()
        mgr.initialize()
        custom = VoiceProfile(
            profile_id="my_custom", name="My Custom",
            personality=PersonalityType.CUSTOM,
            style=SpeakingStyleConfig(speech_rate=0.8, response_length="long"),
            confirmation_phrases=["Affirmative!", "Will do, boss!"],
            greeting="Hey boss!")
        mgr.create_profile(custom)
        mgr.switch_profile("my_custom")
        assert mgr.active_profile.greeting == "Hey boss!"
        assert mgr.get_confirmation_phrase() in ["Affirmative!", "Will do, boss!"]

    def test_adaptation_events(self):
        mgr = VoiceIdentityManager()
        events = []
        mgr.on(IdentityEventType.ADAPTATION_TRIGGERED, lambda ev: events.append(ev))
        mgr.on(IdentityEventType.PROFILE_CHANGED, lambda ev: events.append(ev))
        mgr.initialize()
        mgr.adapt_to_context(AdaptationContext.CODING)
        assert len(events) >= 2
