"""Personality Profiles — built-in voice personalities for EVE."""

from __future__ import annotations

from .models import VoiceProfile, PersonalityType, SpeakingStyleConfig


def _professional() -> VoiceProfile:
    return VoiceProfile(
        profile_id="professional", name="Professional",
        personality=PersonalityType.PROFESSIONAL, is_builtin=True,
        style=SpeakingStyleConfig(speech_rate=1.0, pause_duration_ms=250, sentence_pacing=1.0,
                                  emphasis_strength=0.4, response_length="medium",
                                  confirmation_frequency=0.3, technical_wording=False, natural_wording=True),
        confirmation_phrases=["Understood.", "Noted.", "Will do.", "Confirmed."],
        greeting="How can I help you today?",
        farewell="Let me know if you need anything else.",
        error_prefix="I encountered an issue:",
        success_prefix="Done.",
        verbosity=0.5, sentence_rhythm=1.0)

def _friendly() -> VoiceProfile:
    return VoiceProfile(
        profile_id="friendly", name="Friendly",
        personality=PersonalityType.FRIENDLY, is_builtin=True,
        style=SpeakingStyleConfig(speech_rate=1.05, pause_duration_ms=200, sentence_pacing=1.1,
                                  emphasis_strength=0.5, response_length="medium",
                                  confirmation_frequency=0.4, technical_wording=False, natural_wording=True,
                                  filler_usage=0.15),
        confirmation_phrases=["Sure!", "Got it!", "No problem!", "Happy to help!"],
        greeting="Hey! What can I do for you?",
        farewell="Take care! I'm here if you need me.",
        error_prefix="Hmm, something went wrong:",
        success_prefix="All done!",
        verbosity=0.6, sentence_rhythm=1.1)

def _technical() -> VoiceProfile:
    return VoiceProfile(
        profile_id="technical", name="Technical",
        personality=PersonalityType.TECHNICAL, is_builtin=True,
        style=SpeakingStyleConfig(speech_rate=1.1, pause_duration_ms=150, sentence_pacing=0.9,
                                  emphasis_strength=0.3, response_length="long",
                                  confirmation_frequency=0.2, technical_wording=True, natural_wording=False),
        confirmation_phrases=["Acknowledged.", "Processing.", "Executing."],
        greeting="Ready.",
        farewell="Standing by.",
        error_prefix="Error:",
        success_prefix="Complete.",
        verbosity=0.7, sentence_rhythm=0.9)

def _minimal() -> VoiceProfile:
    return VoiceProfile(
        profile_id="minimal", name="Minimal",
        personality=PersonalityType.MINIMAL, is_builtin=True,
        style=SpeakingStyleConfig(speech_rate=1.2, pause_duration_ms=100, sentence_pacing=0.8,
                                  emphasis_strength=0.2, response_length="short",
                                  confirmation_frequency=0.1, technical_wording=False, natural_wording=True),
        confirmation_phrases=["OK.", "Done.", "Yes."],
        greeting="Yes?",
        farewell="Bye.",
        error_prefix="Issue:",
        success_prefix="Done.",
        verbosity=0.2, sentence_rhythm=0.8)

def _companion() -> VoiceProfile:
    return VoiceProfile(
        profile_id="companion", name="Companion",
        personality=PersonalityType.COMPANION, is_builtin=True,
        style=SpeakingStyleConfig(speech_rate=0.95, pause_duration_ms=300, sentence_pacing=1.2,
                                  emphasis_strength=0.6, response_length="long",
                                  confirmation_frequency=0.5, technical_wording=False, natural_wording=True,
                                  filler_usage=0.2),
        confirmation_phrases=["Of course!", "I'm here for you.", "Absolutely!", "You got it!"],
        greeting="Hey there! How are you doing?",
        farewell="Take care of yourself! I'll be here.",
        error_prefix="Oh no, I ran into a problem:",
        success_prefix="Yay, it worked!",
        verbosity=0.8, sentence_rhythm=1.2)

def _teacher() -> VoiceProfile:
    return VoiceProfile(
        profile_id="teacher", name="Teacher",
        personality=PersonalityType.TEACHER, is_builtin=True,
        style=SpeakingStyleConfig(speech_rate=0.9, pause_duration_ms=350, sentence_pacing=1.3,
                                  emphasis_strength=0.6, response_length="long",
                                  confirmation_frequency=0.4, technical_wording=False, natural_wording=True,
                                  filler_usage=0.1),
        confirmation_phrases=["Great question!", "Let me explain.", "Here's what's happening."],
        greeting="What would you like to learn about?",
        farewell="Keep learning! I'm here whenever you need me.",
        error_prefix="Let me clarify that:",
        success_prefix="Excellent!",
        verbosity=0.8, sentence_rhythm=1.3)

def _creative() -> VoiceProfile:
    return VoiceProfile(
        profile_id="creative", name="Creative",
        personality=PersonalityType.CREATIVE, is_builtin=True,
        style=SpeakingStyleConfig(speech_rate=1.0, pause_duration_ms=250, sentence_pacing=1.15,
                                  emphasis_strength=0.7, response_length="long",
                                  confirmation_frequency=0.3, technical_wording=False, natural_wording=True,
                                  filler_usage=0.15),
        confirmation_phrases=["Love it!", "Interesting approach!", "Let's explore that."],
        greeting="What are we creating today?",
        farewell="Keep creating amazing things!",
        error_prefix="Hmm, let me try a different approach:",
        success_prefix="Beautiful result!",
        verbosity=0.7, sentence_rhythm=1.15)

def _executive() -> VoiceProfile:
    return VoiceProfile(
        profile_id="executive", name="Executive",
        personality=PersonalityType.EXECUTIVE, is_builtin=True,
        style=SpeakingStyleConfig(speech_rate=1.05, pause_duration_ms=200, sentence_pacing=0.9,
                                  emphasis_strength=0.5, response_length="short",
                                  confirmation_frequency=0.2, technical_wording=False, natural_wording=False),
        confirmation_phrases=["Understood.", "Will proceed.", "Noted."],
        greeting="How can I assist?",
        farewell="Let me know if anything changes.",
        error_prefix="Issue detected:",
        success_prefix="Resolved.",
        verbosity=0.3, sentence_rhythm=0.9)


BUILTIN_PROFILES: dict[str, VoiceProfile] = {
    "professional": _professional(),
    "friendly": _friendly(),
    "technical": _technical(),
    "minimal": _minimal(),
    "companion": _companion(),
    "teacher": _teacher(),
    "creative": _creative(),
    "executive": _executive(),
}


def get_builtin_profile(profile_id: str) -> VoiceProfile:
    if profile_id not in BUILTIN_PROFILES:
        raise ValueError(f"Unknown builtin profile: {profile_id}")
    return BUILTIN_PROFILES[profile_id]


def list_builtin_profiles() -> list[VoiceProfile]:
    return list(BUILTIN_PROFILES.values())
