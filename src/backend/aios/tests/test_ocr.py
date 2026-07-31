"""Tests for OCR text extraction module."""

import pytest
from unittest.mock import patch, MagicMock
from PIL import Image

from aios.vision.ocr import _check_tesseract, extract_text, extract_text_with_details, redact_sensitive


@pytest.fixture
def small_image():
    img = Image.new("RGB", (100, 30), color="white")
    return img


class TestCheckTesseract:
    def test_returns_false_when_not_installed(self):
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = None
        with patch("shutil.which", return_value=None), \
             patch.dict("sys.modules", {"pytesseract": None}):
            result = _check_tesseract()
            assert result is False

    def test_caches_result(self):
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = True
        result = _check_tesseract()
        assert result is True
        mod._TESSERACT_AVAILABLE = None

    def test_resets_cache(self):
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = None
        with patch("shutil.which", return_value=None), \
             patch.dict("sys.modules", {"pytesseract": None}):
            result = _check_tesseract()
            assert result is False
            mod._TESSERACT_AVAILABLE = None


class TestExtractText:
    @pytest.mark.asyncio
    async def test_returns_empty_when_tesseract_unavailable(self, small_image):
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = False
        result = await extract_text(small_image)
        assert result == ""

    @pytest.mark.asyncio
    async def test_returns_text_when_tesseract_available(self, small_image):
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = True
        mock_pt = MagicMock()
        mock_pt.image_to_string.return_value = "Hello World"
        with patch.dict("sys.modules", {"pytesseract": mock_pt}):
            result = await extract_text(small_image)
            assert result == "Hello World"

    @pytest.mark.asyncio
    async def test_strips_whitespace(self, small_image):
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = True
        mock_pt = MagicMock()
        mock_pt.image_to_string.return_value = "  Hello  "
        with patch.dict("sys.modules", {"pytesseract": mock_pt}):
            result = await extract_text(small_image)
            assert result == "Hello"

    @pytest.mark.asyncio
    async def test_returns_empty_on_exception(self, small_image):
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = True
        mock_pt = MagicMock()
        mock_pt.image_to_string.side_effect = RuntimeError("ocr failed")
        with patch.dict("sys.modules", {"pytesseract": mock_pt}):
            result = await extract_text(small_image)
            assert result == ""


class TestExtractTextWithDetails:
    @pytest.mark.asyncio
    async def test_returns_error_when_unavailable(self, small_image):
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = False
        result = await extract_text_with_details(small_image)
        assert result.text == ""
        assert "Tesseract not installed" in result.error

    @pytest.mark.asyncio
    async def test_returns_result_with_blocks(self, small_image):
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = True
        mock_pt = MagicMock()
        mock_pt.Output.DICT = "dict"
        mock_pt.image_to_data.return_value = {
            "text": ["Hello", "World"],
            "conf": ["95", "88"],
            "left": [10, 60],
            "top": [5, 5],
            "width": [40, 40],
            "height": [20, 20],
        }
        with patch.dict("sys.modules", {"pytesseract": mock_pt}):
            result = await extract_text_with_details(small_image)
            assert "Hello" in result.text
            assert "World" in result.text
            assert len(result.blocks) == 2
            assert result.confidence > 0


class TestRedactSensitive:
    @pytest.mark.asyncio
    async def test_redacts_ssn(self):
        result = await redact_sensitive("My SSN is 123-45-6789")
        assert "123-45-6789" not in result
        assert "[REDACTED-SSN]" in result

    @pytest.mark.asyncio
    async def test_redacts_email(self):
        result = await redact_sensitive("Contact me at test@example.com")
        assert "test@example.com" not in result
        assert "[REDACTED-EMAIL]" in result

    @pytest.mark.asyncio
    async def test_redacts_phone(self):
        result = await redact_sensitive("Call 555-123-4567")
        assert "555-123-4567" not in result
        assert "[REDACTED-PHONE]" in result

    @pytest.mark.asyncio
    async def test_no_redaction_for_clean_text(self):
        text = "Hello world, no PII here"
        result = await redact_sensitive(text)
        assert result == text

    @pytest.mark.asyncio
    async def test_multiple_redactions(self):
        text = "SSN: 123-45-6789, Email: a@b.com"
        result = await redact_sensitive(text)
        assert "123-45-6789" not in result
        assert "a@b.com" not in result
