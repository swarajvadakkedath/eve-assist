"""Voice Pipeline — orchestrates the full voice flow: Mic → STT → Conversation → Planner → Execution → TTS → Speaker."""

from collections.abc import AsyncIterator
from typing import Any

from aios.voice.models import VoiceConfig, VoiceState, Transcript, TranscriptStatus
from aios.voice.stt import STTEngine
from aios.voice.tts import TTSEngine
from aios.voice.session import VoiceSession
from aios.voice.events import VoiceEventPublisher
from aios.conversation.interfaces import IConversationService
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class VoicePipeline:
    def __init__(
        self,
        session: VoiceSession,
        stt_engine: STTEngine,
        tts_engine: TTSEngine,
        conversation_service: IConversationService,
        event_publisher: VoiceEventPublisher,
    ):
        self._session = session
        self._stt = stt_engine
        self._tts = tts_engine
        self._conversation = conversation_service
        self._events = event_publisher

    async def process_voice_input(self, text: str) -> AsyncIterator[dict]:
        if not text.strip():
            return

        logger.info("voice.pipeline.processing", text=text[:100])
        async for event in self._session.process_transcript(text):
            yield event

    async def process_and_speak(self, text: str) -> dict:
        if not text.strip():
            return {"error": "Empty input"}

        response = await self._session.send_text_message(text)
        if "error" in response:
            return response

        content = response.get("content", "")
        if content.strip():
            utterance_id = await self._session.start_speaking(content)
            response["utterance_id"] = utterance_id

        return response

    async def run_full_cycle(self, audio_input: bytes | None = None) -> AsyncIterator[dict]:
        yield {"type": "status", "data": {"state": "listening"}}
        async for transcript in self._stt.recognize_stream():
            if transcript.status == TranscriptStatus.PARTIAL:
                yield {"type": "transcript_partial", "data": {"text": transcript.text}}
                continue
            if not transcript.text.strip():
                continue
            yield {"type": "transcript_final", "data": {"text": transcript.text}}
            yield {"type": "status", "data": {"state": "processing"}}
            async for event in self._conversation.stream_message(
                self._session.conversation_id or "",
                transcript.text,
            ):
                yield event
                if event.get("type") in ("final_response", "token"):
                    response_text = ""
                    if event["type"] == "final_response":
                        response_text = event.get("data", {}).get("content", "")
                    elif event["type"] == "token":
                        response_text = event.get("data", {}).get("text", "")
                    if response_text.strip() and not self._session._barge_in:
                        yield {"type": "status", "data": {"state": "speaking"}}
                        await self._session.start_speaking(response_text)
                        yield {"type": "speaking_done", "data": {}}
            yield {"type": "status", "data": {"state": "idle"}}

    async def cleanup(self):
        await self._session.cleanup()
