"""Speech-to-Text engine — supports multiple STT providers with streaming recognition."""

import asyncio
from collections.abc import AsyncIterator
from typing import Any

from aios.voice.models import STTProvider, STTResult, AudioDevice, Transcript, TranscriptStatus
from aios.utils.logger import get_logger
from aios.error_intelligence import get_error_intelligence

logger = get_logger(__name__)


class STTEngine:
    def __init__(self, provider: STTProvider = STTProvider.WHISPER, config: dict | None = None):
        self._provider = provider
        self._config = config or {}
        self._is_listening = False
        self._language = self._config.get("language", "en-US")
        self._input_device = self._config.get("input_device")
        self._recognizer = None
        self._microphone = None

    @property
    def is_listening(self) -> bool:
        return self._is_listening

    @property
    def provider(self) -> STTProvider:
        return self._provider

    async def initialize(self):
        if self._provider == STTProvider.MOCK:
            return
        try:
            import speech_recognition as sr
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self._config.get("energy_threshold", 300)
            self._recognizer.dynamic_energy_threshold = self._config.get("dynamic_energy", True)
            self._recognizer.pause_threshold = self._config.get("pause_threshold", 0.8)
            if self._input_device:
                mic_index = self._resolve_device_index(self._input_device)
                if mic_index is not None:
                    self._microphone = sr.Microphone(device_index=mic_index)
                else:
                    self._microphone = sr.Microphone()
            else:
                self._microphone = sr.Microphone()
            await asyncio.to_thread(self._adjust_ambient_noise)
            logger.info("stt.initialized", provider=self._provider.value)
        except ImportError:
            logger.warning("stt.speech_recognition_not_available")
            self._provider = STTProvider.MOCK
        except Exception as e:
            logger.error("stt.initialization_failed", error=str(e))
            self._provider = STTProvider.MOCK

    def _adjust_ambient_noise(self):
        """Blocking ambient noise calibration — must run in a thread."""
        if self._microphone and self._recognizer:
            with self._microphone:
                self._recognizer.adjust_for_ambient_noise(self._microphone, duration=1.0)

    async def start_listening(self, language: str | None = None) -> None:
        if self._is_listening:
            return
        self._is_listening = True
        self._language = language or self._language
        logger.info("stt.listening_started", language=self._language)

    async def stop_listening(self) -> None:
        self._is_listening = False
        logger.info("stt.listening_stopped")

    def _resolve_device_index(self, device_name: str) -> int | None:
        try:
            import speech_recognition as sr
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                if device_name.lower() in name.lower():
                    return index
        except Exception:
            pass
        return None

    async def recognize_once(self, timeout: float = 5.0, phrase_time_limit: float = 10.0) -> STTResult:
        if self._provider == STTProvider.MOCK:
            await asyncio.sleep(0.5)
            return STTResult(text="", confidence=0.0, language=self._language, is_final=False)

        try:
            import speech_recognition as sr
            if not self._recognizer or not self._microphone:
                return STTResult(text="", error="STT not initialized", is_final=False)

            with self._microphone:
                audio = self._recognizer.listen(
                    self._microphone,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                )
            return await self._transcribe(audio)
        except sr.WaitTimeoutError:
            return STTResult(text="", confidence=0.0, is_final=False)
        except sr.UnknownValueError:
            return STTResult(text="", confidence=0.0, is_final=False, error="Could not understand audio")
        except sr.RequestError as e:
            try:
                svc = get_error_intelligence()
                svc.capture_exception(e, module="voice.stt", message=f"STT request failed: {e}")
            except Exception:
                pass
            return STTResult(text="", is_final=False, error=f"STT request failed: {e}")
        except Exception as e:
            logger.error("stt.recognize_failed", error=str(e))
            try:
                svc = get_error_intelligence()
                svc.capture_exception(e, module="voice.stt", message=str(e))
            except Exception:
                pass
            return STTResult(text="", is_final=False, error=str(e))

    async def recognize_stream(self) -> AsyncIterator[Transcript]:
        if self._provider == STTProvider.MOCK:
            yield Transcript(text="", status=TranscriptStatus.FINAL, language=self._language)
            return

        try:
            import speech_recognition as sr
            if not self._recognizer or not self._microphone:
                yield Transcript(text="", status=TranscriptStatus.FINAL, error="STT not initialized")
                return

            await asyncio.to_thread(self._calibrate_source)
            while self._is_listening:
                try:
                    audio = await asyncio.to_thread(self._listen_blocking, timeout=1.0, phrase_time_limit=5.0)
                    if audio is None:
                        continue
                    result = await self._transcribe(audio)
                    if result.text:
                        yield Transcript(
                            text=result.text,
                            status=TranscriptStatus.PARTIAL,
                            confidence=result.confidence,
                            language=result.language or self._language,
                        )
                        if result.is_final:
                            yield Transcript(
                                text=result.text,
                                status=TranscriptStatus.FINAL,
                                confidence=result.confidence,
                                language=result.language or self._language,
                            )
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    continue
                except Exception as e:
                    logger.error("stt.stream_error", error=str(e))
                    yield Transcript(text="", status=TranscriptStatus.FINAL, error=str(e))
        except Exception as e:
            logger.error("stt.stream_failed", error=str(e))
            yield Transcript(text="", status=TranscriptStatus.FINAL, error=str(e))

    def _calibrate_source(self):
        """Blocking ambient noise calibration for streaming — must run in a thread."""
        if self._recognizer and self._microphone:
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)

    def _listen_blocking(self, timeout: float = 1.0, phrase_time_limit: float = 5.0):
        """Blocking audio listen — must run in a thread. Returns audio or None on timeout."""
        import speech_recognition as sr
        if not self._recognizer or not self._microphone:
            return None
        with self._microphone as source:
            return self._recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)

    async def _transcribe(self, audio) -> STTResult:
        if not self._recognizer:
            return STTResult(text="", error="Recognizer not initialized", is_final=False)

        try:
            if self._provider == STTProvider.GOOGLE:
                text = await asyncio.to_thread(
                    self._recognizer.recognize_google, audio,
                    language=self._language, show_all=False,
                )
                return STTResult(text=text, confidence=0.8, language=self._language, is_final=True)
            elif self._provider == STTProvider.WHISPER:
                text = await asyncio.to_thread(
                    self._recognizer.recognize_whisper,
                    audio,
                    language=self._language[:2],
                )
                return STTResult(text=text, confidence=0.85, language=self._language, is_final=True)
            elif self._provider == STTProvider.SPHINX:
                text = await asyncio.to_thread(
                    self._recognizer.recognize_sphinx, audio, language=self._language[:2],
                )
                return STTResult(text=text, confidence=0.6, language=self._language, is_final=True)
            elif self._provider == STTProvider.AZURE:
                key = self._config.get("azure_key", "")
                region = self._config.get("azure_region", "")
                if key and region:
                    text = await asyncio.to_thread(
                        self._recognizer.recognize_azure, audio,
                        key=key, location=region, language=self._language,
                    )
                    return STTResult(text=text, confidence=0.9, language=self._language, is_final=True)
            return STTResult(text="", is_final=False, error="No suitable provider")
        except Exception as e:
            return STTResult(text="", is_final=False, error=str(e))

    async def get_available_devices(self) -> list[AudioDevice]:
        devices = []
        try:
            import speech_recognition as sr
            for index, name in enumerate(sr.Microphone.list_microphone_names()):
                devices.append(AudioDevice(
                    id=str(index),
                    name=name,
                    is_default=(index == 0),
                ))
        except Exception:
            pass
        if not devices:
            devices.append(AudioDevice(id="default", name="Default Microphone", is_default=True))
        return devices

    def update_config(self, config: dict):
        self._config.update(config)
        if "language" in config:
            self._language = config["language"]
        if "input_device" in config:
            self._input_device = config["input_device"]

    async def cleanup(self):
        self._is_listening = False
        self._recognizer = None
        self._microphone = None
