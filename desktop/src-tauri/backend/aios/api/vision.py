"""REST API routes for the Vision Interface."""

import base64
from io import BytesIO

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from aios.vision.session import VisionSession
from aios.vision.models import VisionConfig, VisionProvider, OCREngine, ObservationMode, CaptureTarget

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])

vision_session: VisionSession | None = None


def _get_session() -> VisionSession:
    if vision_session is None:
        raise HTTPException(status_code=503, detail="Vision service not initialized")
    return vision_session


class CaptureRequest(BaseModel):
    target: str = "full_screen"
    monitor_id: int = 0
    region: list[int] | None = None


class ConfigUpdate(BaseModel):
    provider: str | None = None
    ocr_engine: str | None = None
    capture_quality: int | None = None
    auto_redact: bool | None = None
    observation_mode: str | None = None


@router.post("/capture")
async def capture(req: CaptureRequest):
    session = _get_session()
    engine = session.engine
    try:
        if req.target == "window":
            result = await engine.capture_window()
        elif req.target == "region" and req.region:
            region = tuple(req.region)
            result = await engine.capture_region(region)
        elif req.target == "monitor":
            result = await engine.capture_monitor(req.monitor_id)
        else:
            result = await engine.capture_screen()
        b64 = base64.b64encode(result.image_data).decode("utf-8")
        return {
            "image": f"data:image/{result.format};base64,{b64}",
            "width": result.width,
            "height": result.height,
            "format": result.format,
            "size_bytes": len(result.image_data),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze(req: CaptureRequest):
    session = _get_session()
    try:
        observation = await session.analyze_current_screen()
        return {
            "summary": observation.summary,
            "ocr_text": observation.ocr.text if observation.ocr else "",
            "ocr_confidence": observation.ocr.confidence if observation.ocr else 0,
            "ui_elements": [
                {"type": e.type, "text": e.text, "x": e.x, "y": e.y, "w": e.width, "h": e.height}
                for e in (observation.detection.elements if observation.detection else [])
            ],
            "layout": [
                {"type": r.region_type, "x": r.x, "y": r.y, "w": r.width, "h": r.height, "label": r.label}
                for r in (observation.detection.layout if observation.detection else [])
            ],
            "element_count": len(observation.detection.elements) if observation.detection else 0,
            "duration_ms": observation.detection.duration_ms if observation.detection else 0,
            "observation_id": observation.id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-upload")
async def analyze_upload(file: UploadFile = File(...)):
    session = _get_session()
    try:
        contents = await file.read()
        observation = await session.analyze_uploaded_image(contents)
        return {
            "summary": observation.summary,
            "ocr_text": observation.ocr.text if observation.ocr else "",
            "ui_elements": [
                {"type": e.type, "text": e.text, "x": e.x, "y": e.y, "w": e.width, "h": e.height}
                for e in (observation.detection.elements if observation.detection else [])
            ],
            "element_count": len(observation.detection.elements) if observation.detection else 0,
            "observation_id": observation.id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/observation/latest")
async def get_latest_observation():
    session = _get_session()
    state = await session.get_state()
    obs = state.last_observation
    if not obs:
        raise HTTPException(status_code=404, detail="No observations yet")
    return {
        "id": obs.id,
        "summary": obs.summary,
        "ocr_text": obs.ocr.text if obs.ocr else "",
        "element_count": len(obs.detection.elements) if obs.detection else 0,
        "total_observations": state.observation_count,
    }


@router.post("/session/start")
async def start_session():
    session = _get_session()
    state = await session.start("vision-api-session")
    return {"session_id": state.session_id, "mode": state.observation_mode.value}


@router.post("/session/stop")
async def stop_session():
    session = _get_session()
    state = await session.stop()
    return {"observations": state.observation_count}


@router.get("/config")
async def get_config():
    session = _get_session()
    config = session.config
    return {
        "provider": config.provider.value,
        "ocr_engine": config.ocr_engine.value,
        "capture_quality": config.capture_quality,
        "privacy_filters": config.privacy_filters_enabled,
        "auto_redact": config.auto_redact_sensitive,
        "observation_mode": config.observation_mode.value,
    }


@router.put("/config")
async def update_config(update: ConfigUpdate):
    session = _get_session()
    config = session.config
    if update.provider:
        config.provider = VisionProvider(update.provider)
    if update.ocr_engine:
        config.ocr_engine = OCREngine(update.ocr_engine)
    if update.capture_quality:
        config.capture_quality = update.capture_quality
    if update.auto_redact is not None:
        config.auto_redact_sensitive = update.auto_redact
    if update.observation_mode:
        config.observation_mode = ObservationMode(update.observation_mode)
    await session.update_config(config)
    return {"status": "ok"}


@router.get("/providers")
async def list_providers():
    session = _get_session()
    providers = await session.engine.get_providers()
    return {"providers": providers}


@router.get("/monitors")
async def list_monitors():
    session = _get_session()
    monitors = await session.engine.get_monitors()
    return {"monitors": monitors}
