"""VisionSession — manages observation lifecycle for a conversation session."""

import time
from datetime import datetime, timezone
from io import BytesIO

from PIL import Image

from aios.vision.models import (
    VisionConfig, VisionSessionState, VisionObservation,
    ObservationMode, VisionProvider,
)
from aios.vision.engine import VisionEngine


class VisionSession:
    """Manages observations tied to a conversation session."""

    def __init__(self, engine: VisionEngine | None = None, config: VisionConfig | None = None):
        self.config = config or VisionConfig()
        self.engine = engine or VisionEngine(self.config)
        self.state: VisionSessionState = VisionSessionState()

    async def start(self, session_id: str, mode: ObservationMode = ObservationMode.MANUAL) -> VisionSessionState:
        self.state = VisionSessionState(
            session_id=session_id,
            is_observing=True,
            observation_mode=mode,
            started_at=datetime.now(timezone.utc),
        )
        return self.state

    async def stop(self) -> VisionSessionState:
        self.state.is_observing = False
        return self.state

    async def analyze_current_screen(self) -> VisionObservation:
        obs = await self.engine.full_observation()
        obs.session_id = self.state.session_id
        self.state.last_observation = obs
        self.state.observation_count += 1
        return obs

    async def analyze_uploaded_image(self, image_data: bytes) -> VisionObservation:
        from aios.vision.screenshot import ScreenshotResult
        start = time.monotonic()
        screenshot = ScreenshotResult(image_data=image_data)
        ocr = await self.engine.ocr_image_from_bytes(image_data)
        detection = await self.engine.analyze_image(image_data)
        duration = (time.monotonic() - start) * 1000
        if detection:
            detection.duration_ms = duration

        summary = f"Analyzed uploaded image"
        if ocr and ocr.text:
            summary += f" — text: {ocr.text[:100]}"

        obs = VisionObservation(
            session_id=self.state.session_id,
            screenshot=screenshot,
            ocr=ocr,
            detection=detection,
            summary=summary,
            context={
                "source": "upload",
                "duration_ms": duration,
            },
        )
        self.state.last_observation = obs
        self.state.observation_count += 1
        return obs

    async def get_state(self) -> VisionSessionState:
        return self.state

    async def update_config(self, config: VisionConfig) -> VisionConfig:
        self.config = config
        self.engine.config = config
        return self.config

    async def capture_current(self) -> bytes:
        return await self.engine.get_screenshot_bytes()
