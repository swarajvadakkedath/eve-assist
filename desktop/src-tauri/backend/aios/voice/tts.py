"""Text-to-Speech engine — supports multiple TTS providers with streaming output."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from aios.voice.models import TTSProvider, TTSRequest, AudioDevice
from aios.utils.logger import get_logger

logger = get_logger(__name__)


class TTSEngine:
    def __init__(self, provider: TTSProvider = TTSProvider.PYTTSX3, config: dict | None = None):
        self._provider = provider
        self._config = config or {}
        self._is_speaking = False
        self._should_stop = False
        self._queue: asyncio.Queue[TTSRequest] = asyncio.Queue()
        self._current_utterance: TTSRequest | None = None
        self._engine = None
        self._voice_id = self._config.get("voice_id", "")
        self._rate = self._config.get("rate", 150)
        self._pitch = self._config.get("pitch", 1.0)
        self._worker_task: asyncio.Task | None = None

    @property
    def is_speaking(self) -> bool:
        return self._is_speaking

    @property
    def provider(self) -> TTSProvider:
        return self._provider

    async def initialize(self):
        if self._provider == TTSProvider.MOCK:
            self._worker_task = asyncio.create_task(self._mock_worker())
            return
        try:
            if self._provider == TTSProvider.PYTTSX3:
                import pyttsx3
                self._engine = pyttsx3.init()
                self._apply_voice_settings()
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("tts.initialized", provider=self._provider.value)
        except ImportError:
            logger.warning("tts.pyttsx3_not_available")
            self._provider = TTSProvider.MOCK
            self._worker_task = asyncio.create_task(self._mock_worker())
        except Exception as e:
            logger.error("tts.initialization_failed", error=str(e))
            self._provider = TTSProvider.MOCK
            self._worker_task = asyncio.create_task(self._mock_worker())

    def _apply_voice_settings(self):
        if not self._engine:
            return
        try:
            voices = self._engine.getProperty("voices")
            if self._voice_id:
                for v in voices:
                    if self._voice_id in v.id:
                        self._engine.setProperty("voice", v.id)
                        break
            self._engine.setProperty("rate", self._rate)
            self._engine.setProperty("volume", self._config.get("volume", 1.0))
        except Exception as e:
            logger.error("tts.apply_voice_failed", error=str(e))

    async def speak(self, text: str, request: TTSRequest | None = None) -> str:
        if not text.strip():
            return ""
        req = request or TTSRequest(text=text, voice_id=self._voice_id, rate=self._rate, pitch=self._pitch)
        await self._queue.put(req)
        return req.utterance_id

    async def speak_stream(self, text_stream: AsyncIterator[str]) -> str:
        utterance_id = ""
        async for chunk in text_stream:
            if self._should_stop:
                break
            if chunk.strip():
                req = TTSRequest(text=chunk, voice_id=self._voice_id, rate=self._rate, pitch=self._pitch)
                if not utterance_id:
                    utterance_id = req.utterance_id
                await self._queue.put(req)
        return utterance_id

    async def stop(self):
        self._should_stop = True
        if self._engine and self._provider == TTSProvider.PYTTSX3:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._is_speaking = False
        self._current_utterance = None
        while not self._queue.empty():
            try:
                self._queue.get_nowait()
                self._queue.task_done()
            except asyncio.QueueEmpty:
                break
        self._should_stop = False
        logger.info("tts.stopped")

    def set_voice(self, voice_id: str):
        self._voice_id = voice_id
        if self._engine and self._provider == TTSProvider.PYTTSX3:
            try:
                voices = self._engine.getProperty("voices")
                for v in voices:
                    if voice_id in v.id:
                        self._engine.setProperty("voice", v.id)
                        break
            except Exception as e:
                logger.error("tts.set_voice_failed", error=str(e))

    def set_rate(self, rate: float):
        self._rate = int(rate)
        if self._engine and self._provider == TTSProvider.PYTTSX3:
            try:
                self._engine.setProperty("rate", self._rate)
            except Exception as e:
                logger.error("tts.set_rate_failed", error=str(e))

    def set_pitch(self, pitch: float):
        self._pitch = pitch

    async def _worker_loop(self):
        while True:
            try:
                request = await self._queue.get()
                if self._should_stop:
                    self._queue.task_done()
                    continue
                self._current_utterance = request
                self._is_speaking = True
                await self._speech_sync(request)
                self._is_speaking = False
                self._current_utterance = None
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("tts.worker_error", error=str(e))
                self._is_speaking = False
                self._current_utterance = None

    async def _speech_sync(self, request: TTSRequest):
        if self._provider == TTSProvider.PYTTSX3 and self._engine:
            try:
                await asyncio.to_thread(self._engine.say, request.text)
                await asyncio.to_thread(self._engine.runAndWait)
            except Exception as e:
                logger.error("tts.speak_failed", error=str(e))
        elif self._provider == TTSProvider.MOCK:
            duration = max(0.1, len(request.text) * 0.02)
            await asyncio.sleep(duration)

    async def _mock_worker(self):
        while True:
            try:
                request = await asyncio.wait_for(self._queue.get(), timeout=None)
                self._current_utterance = request
                self._is_speaking = True
                duration = max(0.1, len(request.text) * 0.02)
                await asyncio.sleep(duration)
                self._is_speaking = False
                self._current_utterance = None
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception:
                self._is_speaking = False
                self._current_utterance = None

    def is_processing(self, utterance_id: str) -> bool:
        if self._current_utterance and self._current_utterance.utterance_id == utterance_id:
            return True
        return False

    async def get_available_voices(self) -> list[dict[str, Any]]:
        voices = []
        try:
            if self._provider == TTSProvider.PYTTSX3:
                import pyttsx3
                engine = pyttsx3.init()
                for v in engine.getProperty("voices"):
                    voices.append({
                        "id": v.id,
                        "name": v.name,
                        "languages": v.languages,
                        "gender": v.gender,
                    })
                engine.stop()
        except Exception:
            pass
        if not voices:
            voices = [
                {"id": "default", "name": "Default Voice", "languages": ["en"], "gender": "neutral"},
            ]
        return voices

    async def get_available_devices(self) -> list[AudioDevice]:
        devices = []
        try:
            import pyttsx3
            engine = pyttsx3.init()
            voices = engine.getProperty("voices")
            for i, v in enumerate(voices):
                devices.append(AudioDevice(
                    id=v.id,
                    name=v.name or f"Voice {i}",
                    is_default=(i == 0),
                ))
            engine.stop()
        except Exception:
            pass
        if not devices:
            devices.append(AudioDevice(id="default", name="Default Output", is_default=True))
        return devices

    def update_config(self, config: dict):
        self._config.update(config)
        if "voice_id" in config:
            self.set_voice(config["voice_id"])
        if "rate" in config:
            self.set_rate(config["rate"])
        if "pitch" in config:
            self.set_pitch(config["pitch"])

    async def cleanup(self):
        await self.stop()
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
        if self._engine and self._provider == TTSProvider.PYTTSX3:
            try:
                self._engine.stop()
            except Exception:
                pass
        self._engine = None
