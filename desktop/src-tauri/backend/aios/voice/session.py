"""Voice Session — manages start/stop listening, speaking, barge-in, and conversation sync."""

import asyncio
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from aios.voice.models import (
    VoiceConfig,
    VoiceState,
    VoiceSessionState,
    Transcript,
    TranscriptStatus,
    STTResult,
    TTSRequest,
)
from aios.voice.stt import STTEngine
from aios.voice.tts import TTSEngine
from aios.voice.events import VoiceEventPublisher
from aios.conversation.interfaces import IConversationService
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class BargeInError(Exception):
    pass


class VoiceSession:
    def __init__(
        self,
        stt_engine: STTEngine,
        tts_engine: TTSEngine,
        conversation_service: IConversationService,
        event_publisher: VoiceEventPublisher,
        config: VoiceConfig | None = None,
    ):
        self._stt = stt_engine
        self._tts = tts_engine
        self._conversation = conversation_service
        self._events = event_publisher
        self._config = config or VoiceConfig()
        self._state = VoiceSessionState()
        self._listener_task: asyncio.Task | None = None
        self._barge_in = False
        self._lock = asyncio.Lock()
        self._personality_manager = None

    @property
    def state(self) -> VoiceSessionState:
        return self._state

    @property
    def is_listening(self) -> bool:
        return self._state.is_listening

    @property
    def is_speaking(self) -> bool:
        return self._state.is_speaking

    @property
    def conversation_id(self) -> str | None:
        return self._state.conversation_id

    async def start_session(self, conversation_id: str | None = None) -> str:
        async with self._lock:
            self._state = VoiceSessionState(
                state=VoiceState.IDLE,
                conversation_id=conversation_id or "",
            )
            await self._stt.initialize()
            await self._tts.initialize()
            if not self._state.conversation_id:
                conv = await self._conversation.create_conversation(title="Voice Session")
                self._state.conversation_id = conv.id
            logger.info("voice.session_started", session_id=self._state.session_id)
            return self._state.session_id

    async def start_listening(self, language: str | None = None) -> None:
        async with self._lock:
            if self._state.is_listening:
                return
            await self._set_state(VoiceState.LISTENING)
            self._state.is_listening = True
            self._state.current_transcript = ""
            await self._stt.start_listening(language or self._config.language)
            await self._events.publish_listening_start(
                self._state.session_id,
                device=self._config.input_device,
            )
            self._listener_task = asyncio.create_task(self._listen_loop())

    async def stop_listening(self) -> str | None:
        async with self._lock:
            if not self._state.is_listening:
                return None
            self._state.is_listening = False
            await self._stt.stop_listening()
            await self._events.publish_listening_stop(self._state.session_id)
            if self._listener_task:
                self._listener_task.cancel()
                try:
                    await self._listener_task
                except asyncio.CancelledError:
                    pass
                self._listener_task = None
            final_text = self._state.current_transcript.strip()
            await self._set_state(VoiceState.IDLE)
            return final_text if final_text else None

    async def start_speaking(self, text: str) -> str | None:
        async with self._lock:
            if not text.strip():
                return None
            if self._state.is_speaking and self._barge_in:
                await self._interrupt_speaking()
            await self._set_state(VoiceState.SPEAKING)
            utterance_id = await self._tts.speak(text)
            self._state.is_speaking = True
            await self._events.publish_speaking_start(self._state.session_id, utterance_id)
            return utterance_id

    async def stop_speaking(self, reason: str = "manual") -> None:
        async with self._lock:
            if not self._state.is_speaking:
                return
            await self._interrupt_speaking()
            await self._events.publish_speaking_stop(
                self._state.session_id,
                self._tts._current_utterance.utterance_id if self._tts._current_utterance else "",
                reason=reason,
            )
            await self._set_state(VoiceState.IDLE)

    async def barge_in(self) -> None:
        self._barge_in = True
        await self.stop_speaking(reason="barge_in")
        logger.info("voice.barge_in_triggered")
        self._barge_in = False

    async def process_transcript(self, text: str) -> AsyncIterator[dict]:
        if not text.strip() or not self._state.conversation_id:
            return
        await self._set_state(VoiceState.PROCESSING)
        try:
            async for event in self._conversation.stream_message(
                self._state.conversation_id, text
            ):
                yield event
                if event.get("type") == "final_response" or event.get("type") == "token":
                    response_text = ""
                    if event["type"] == "final_response":
                        response_text = event.get("data", {}).get("content", "")
                    elif event["type"] == "token":
                        response_text = event.get("data", {}).get("text", "")
                    if response_text.strip():
                        formatted = response_text
                        if self._personality_manager is not None:
                            formatted = self._personality_manager.format_response(
                                response_text, context="voice"
                            )
                        if not self._barge_in:
                            await self.start_speaking(formatted)
        except Exception as e:
            logger.error("voice.process_transcript_failed", error=str(e))
            await self._events.publish_error(self._state.session_id, str(e))
        finally:
            await self._set_state(VoiceState.IDLE)

    async def send_text_message(self, text: str) -> dict:
        if not text.strip() or not self._state.conversation_id:
            return {"error": "No conversation active"}
        await self._set_state(VoiceState.PROCESSING)
        try:
            response = await self._conversation.send_message(
                self._state.conversation_id, text
            )
            return {
                "conversation_id": response.conversation_id,
                "message_id": response.id,
                "content": response.content,
                "role": response.role.value if hasattr(response.role, "value") else response.role,
            }
        except Exception as e:
            logger.error("voice.send_message_failed", error=str(e))
            return {"error": str(e)}
        finally:
            await self._set_state(VoiceState.IDLE)

    def set_conversation(self, conversation_id: str):
        self._state.conversation_id = conversation_id

    def update_config(self, config: VoiceConfig):
        self._config = config
        self._stt.update_config({
            "language": config.language,
            "input_device": config.input_device,
        })
        self._tts.update_config({
            "voice_id": config.voice_id,
            "rate": config.speaking_rate,
            "pitch": config.pitch,
        })

    async def _listen_loop(self):
        try:
            async for transcript in self._stt.recognize_stream():
                if not self._state.is_listening:
                    break
                self._state.current_transcript = transcript.text
                if transcript.status == TranscriptStatus.PARTIAL:
                    await self._events.publish_transcript_partial(
                        self._state.session_id,
                        transcript.text,
                        transcript.confidence,
                    )
                elif transcript.status == TranscriptStatus.FINAL and transcript.text.strip():
                    await self._events.publish_transcript_final(
                        self._state.session_id,
                        transcript.text,
                        transcript.confidence,
                    )
                    async for _ in self.process_transcript(transcript.text):
                        pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error("voice.listen_loop_error", error=str(e))
            await self._events.publish_error(self._state.session_id, str(e))
        finally:
            self._state.is_listening = False
            await self._set_state(VoiceState.IDLE)

    async def _interrupt_speaking(self):
        self._state.is_speaking = False
        await self._tts.stop()

    async def _set_state(self, new_state: VoiceState):
        previous = self._state.state
        self._state.state = new_state
        await self._events.publish_state_change(
            self._state.session_id,
            new_state.value,
            previous.value,
        )

    async def cleanup(self):
        if self._listener_task:
            self._listener_task.cancel()
            try:
                await self._listener_task
            except asyncio.CancelledError:
                pass
            self._listener_task = None
        await self._stt.cleanup()
        await self._tts.cleanup()
        self._state.state = VoiceState.IDLE
        self._state.is_listening = False
        self._state.is_speaking = False
        logger.info("voice.session_cleaned", session_id=self._state.session_id)
