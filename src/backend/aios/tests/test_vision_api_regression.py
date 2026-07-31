"""Regression: analyze_upload must use module-level vision_pipeline (scoping fix).

The bug: app.py sets `aios.api.vision.vision_pipeline = pipeline` as a module attribute,
but analyze_upload read a local variable `vision_pipeline` that stayed None.

Fix: _get_pipeline() reads via sys.modules[__name__] at call time.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import UploadFile

from aios.vision.models import VisionConfig, VisionProvider, OCREngine, VisionObservation, OCRResult, DetectionResult


@pytest.fixture
def mock_observation():
    return VisionObservation(
        session_id="test-session",
        screenshot=None,
        ocr=OCRResult(text="observed text", confidence=0.9),
        detection=DetectionResult(elements=[]),
        summary="test observation",
    )


class TestGetPipeline:
    """Regression: _get_pipeline reads module-level vision_pipeline via sys.modules."""

    def test_returns_none_when_not_set(self):
        import aios.api.vision as mod
        old = getattr(mod, "vision_pipeline", None)
        try:
            mod.vision_pipeline = None
            from aios.api.vision import _get_pipeline
            result = _get_pipeline()
            assert result is None
        finally:
            mod.vision_pipeline = old

    def test_returns_pipeline_when_set(self):
        import aios.api.vision as mod
        old = getattr(mod, "vision_pipeline", None)
        try:
            fake_pipeline = MagicMock()
            mod.vision_pipeline = fake_pipeline
            from aios.api.vision import _get_pipeline
            result = _get_pipeline()
            assert result is fake_pipeline
        finally:
            mod.vision_pipeline = old


class TestGetSession:
    """Regression: _get_session reads module-level vision_session via sys.modules."""

    def test_raises_when_not_set(self):
        import aios.api.vision as mod
        old = getattr(mod, "vision_session", None)
        try:
            mod.vision_session = None
            from aios.api.vision import _get_session
            with pytest.raises(Exception):
                _get_session()
        finally:
            mod.vision_session = old

    def test_returns_session_when_set(self):
        import aios.api.vision as mod
        old = getattr(mod, "vision_session", None)
        try:
            fake_session = MagicMock()
            fake_session.state.session_id = "test-id"
            mod.vision_session = fake_session
            from aios.api.vision import _get_session
            result = _get_session()
            assert result is fake_session
        finally:
            mod.vision_session = old


class TestAnalyzeUploadPipelinePath:
    """Regression: analyze_upload uses module-level vision_pipeline, not a local shadow."""

    @pytest.mark.asyncio
    async def test_uses_module_level_pipeline(self, mock_observation):
        import aios.api.vision as mod
        old_pipeline = getattr(mod, "vision_pipeline", None)
        old_session = getattr(mod, "vision_session", None)
        try:
            mock_session = MagicMock()
            mock_session.state.session_id = "sess-1"
            mock_pipeline = AsyncMock()
            mock_pipeline.observe_image = AsyncMock(return_value=mock_observation)

            mod.vision_pipeline = mock_pipeline
            mod.vision_session = mock_session

            from aios.api.vision import analyze_upload

            fake_file = AsyncMock(spec=UploadFile)
            fake_file.read = AsyncMock(return_value=b"fake_image_data")

            result = await analyze_upload(file=fake_file)

            mock_pipeline.observe_image.assert_called_once()
            assert result["ocr_text"] == "observed text"
        finally:
            mod.vision_pipeline = old_pipeline
            mod.vision_session = old_session

    @pytest.mark.asyncio
    async def test_falls_back_to_session_when_pipeline_none(self, mock_observation):
        import aios.api.vision as mod
        old_pipeline = getattr(mod, "vision_pipeline", None)
        old_session = getattr(mod, "vision_session", None)
        try:
            mock_session = AsyncMock()
            mock_session.state.session_id = "sess-2"
            mock_session.analyze_uploaded_image = AsyncMock(return_value=mock_observation)

            mod.vision_pipeline = None
            mod.vision_session = mock_session

            from aios.api.vision import analyze_upload

            fake_file = AsyncMock(spec=UploadFile)
            fake_file.read = AsyncMock(return_value=b"fake_image_data")

            result = await analyze_upload(file=fake_file)

            mock_session.analyze_uploaded_image.assert_called_once()
            assert result["ocr_text"] == "observed text"
        finally:
            mod.vision_pipeline = old_pipeline
            mod.vision_session = old_session
