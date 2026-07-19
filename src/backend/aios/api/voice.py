"""Voice API routes — REST + WebSocket for voice interface."""

import json
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from aios.voice.models import (
    VoiceConfig,
    STTProvider,
    TTSProvider,
    VoiceState,
    AudioDevice,
)
from aios.utils.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


class StartSessionRequest(BaseModel):
    conversation_id: str | None = None


class StartListeningRequest(BaseModel):
    language: str | None = None


class StopListeningRequest(BaseModel):
    pass


class SpeakRequest(BaseModel):
    text: str


class SendTextRequest(BaseModel):
    text: str
    conversation_id: str | None = None


class UpdateConfigRequest(BaseModel):
    config: dict


class SetConversationRequest(BaseModel):
    conversation_id: str


@router.post("/session/start")
async def start_session(req: Request, body: StartSessionRequest):
    session = req.app.state.voice_session
    session_id = await session.start_session(conversation_id=body.conversation_id)
    return {
        "session_id": session_id,
        "conversation_id": session.conversation_id,
        "state": session.state.state.value,
    }


@router.post("/session/stop")
async def stop_session(req: Request):
    session = req.app.state.voice_session
    await session.cleanup()
    return {"status": "stopped"}


@router.post("/listen/start")
async def start_listening(req: Request, body: StartListeningRequest | None = None):
    session = req.app.state.voice_session
    await session.start_listening(language=body.language if body else None)
    return {"status": "listening", "state": session.state.state.value}


@router.post("/listen/stop")
async def stop_listening(req: Request):
    session = req.app.state.voice_session
    text = await session.stop_listening()
    return {"status": "stopped", "transcript": text or "", "state": session.state.state.value}


@router.post("/speak")
async def speak(req: Request, body: SpeakRequest):
    session = req.app.state.voice_session
    utterance_id = await session.start_speaking(body.text)
    return {"status": "speaking", "utterance_id": utterance_id}


@router.post("/speak/stop")
async def stop_speaking(req: Request):
    session = req.app.state.voice_session
    await session.stop_speaking()
    return {"status": "stopped"}


@router.post("/barge-in")
async def barge_in(req: Request):
    session = req.app.state.voice_session
    await session.barge_in()
    return {"status": "interrupted"}


@router.post("/send")
async def send_text(req: Request, body: SendTextRequest):
    session = req.app.state.voice_session
    if body.conversation_id:
        session.set_conversation(body.conversation_id)
    result = await session.send_text_message(body.text)
    return result


@router.post("/conversation")
async def set_conversation(req: Request, body: SetConversationRequest):
    session = req.app.state.voice_session
    session.set_conversation(body.conversation_id)
    return {"status": "ok", "conversation_id": body.conversation_id}


@router.get("/state")
async def get_state(req: Request):
    session = req.app.state.voice_session
    s = session.state
    return {
        "session_id": s.session_id,
        "conversation_id": s.conversation_id,
        "state": s.state.value,
        "is_listening": s.is_listening,
        "is_speaking": s.is_speaking,
        "current_transcript": s.current_transcript,
        "audio_level": s.audio_level,
        "error": s.error,
        "started_at": s.started_at.isoformat() if s.started_at else None,
    }


@router.put("/config")
async def update_config(req: Request, body: UpdateConfigRequest):
    session = req.app.state.voice_session
    config_dict = body.config
    voice_config = VoiceConfig(
        stt_provider=STTProvider(config_dict.get("stt_provider", "whisper")),
        tts_provider=TTSProvider(config_dict.get("tts_provider", "pyttsx3")),
        input_device=config_dict.get("input_device"),
        output_device=config_dict.get("output_device"),
        language=config_dict.get("language", "en-US"),
        voice_id=config_dict.get("voice_id", ""),
        speaking_rate=config_dict.get("speaking_rate", 1.0),
        pitch=config_dict.get("pitch", 1.0),
        push_to_talk_key=config_dict.get("push_to_talk_key", "v"),
        wake_word_enabled=config_dict.get("wake_word_enabled", False),
        wake_word=config_dict.get("wake_word", "hey eve"),
        continuous_listening=config_dict.get("continuous_listening", False),
    )
    session.update_config(voice_config)
    settings_store = req.app.state.settings_store
    if settings_store:
        await settings_store.set("voice", config_dict)
    return {"status": "updated"}


@router.get("/config")
async def get_config(req: Request):
    session = req.app.state.voice_session
    settings_store = req.app.state.settings_store
    saved = {}
    if settings_store:
        saved = await settings_store.get("voice") or {}
    c = session._config
    return {
        "stt_provider": saved.get("stt_provider", c.stt_provider.value),
        "tts_provider": saved.get("tts_provider", c.tts_provider.value),
        "input_device": saved.get("input_device", c.input_device),
        "output_device": saved.get("output_device", c.output_device),
        "language": saved.get("language", c.language),
        "voice_id": saved.get("voice_id", c.voice_id),
        "speaking_rate": saved.get("speaking_rate", c.speaking_rate),
        "pitch": saved.get("pitch", c.pitch),
        "push_to_talk_key": saved.get("push_to_talk_key", c.push_to_talk_key),
        "wake_word_enabled": saved.get("wake_word_enabled", c.wake_word_enabled),
        "wake_word": saved.get("wake_word", c.wake_word),
        "continuous_listening": saved.get("continuous_listening", c.continuous_listening),
    }


@router.get("/devices/input")
async def get_input_devices(req: Request):
    stt = req.app.state.stt_engine
    devices = await stt.get_available_devices()
    return {"devices": [{"id": d.id, "name": d.name, "is_default": d.is_default} for d in devices]}


@router.get("/devices/output")
async def get_output_devices(req: Request):
    tts = req.app.state.tts_engine
    devices = await tts.get_available_devices()
    return {"devices": [{"id": d.id, "name": d.name, "is_default": d.is_default} for d in devices]}


@router.get("/voices")
async def get_voices(req: Request):
    tts = req.app.state.tts_engine
    voices = await tts.get_available_voices()
    return {"voices": voices}


@router.websocket("/ws")
async def voice_websocket(ws: WebSocket):
    await ws.accept()
    session = ws.app.state.voice_session
    event_bus = ws.app.state.event_bus

    async def forward_voice_events(event):
        try:
            await ws.send_json({
                "type": event.type,
                "data": event.payload,
                "timestamp": event.timestamp.isoformat() if event.timestamp else None,
            })
        except Exception:
            pass

    subs = []
    for etype in [
        "voice:listening:start",
        "voice:listening:stop",
        "voice:transcript:partial",
        "voice:transcript:final",
        "voice:speaking:start",
        "voice:speaking:stop",
        "voice:state:change",
        "voice:audio:level",
        "voice:error",
    ]:
        sub_id = await event_bus.subscribe(etype, forward_voice_events)
        subs.append(sub_id)

    try:
        while True:
            data = await ws.receive_json()
            action = data.get("action", "")

            if action == "start_listening":
                await session.start_listening(language=data.get("language"))
                await ws.send_json({"type": "listening:started"})
            elif action == "stop_listening":
                text = await session.stop_listening()
                await ws.send_json({"type": "listening:stopped", "transcript": text or ""})
            elif action == "speak":
                utterance_id = await session.start_speaking(data.get("text", ""))
                await ws.send_json({"type": "speaking:started", "utterance_id": utterance_id})
            elif action == "stop_speaking":
                await session.stop_speaking()
                await ws.send_json({"type": "speaking:stopped"})
            elif action == "barge_in":
                await session.barge_in()
                await ws.send_json({"type": "barge_in:done"})
            elif action == "send_text":
                result = await session.send_text_message(data.get("text", ""))
                await ws.send_json({"type": "message:sent", "data": result})
            elif action == "get_state":
                s = session.state
                await ws.send_json({
                    "type": "state",
                    "data": {
                        "session_id": s.session_id,
                        "state": s.state.value,
                        "is_listening": s.is_listening,
                        "is_speaking": s.is_speaking,
                        "current_transcript": s.current_transcript,
                    },
                })
    except WebSocketDisconnect:
        logger.info("voice.websocket_disconnected")
    except Exception as e:
        logger.error("voice.websocket_error", error=str(e))
    finally:
        for sub_id in subs:
            await event_bus.unsubscribe(sub_id)
