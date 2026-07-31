"""Tests for OCR text extraction module."""

import os
from pathlib import Path
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


class TestFindTesseract:
    """Regression: _find_tesseract resolves Tesseract via PATH or Windows common paths."""

    def test_returns_shutil_which_when_found(self):
        from aios.vision.ocr import _find_tesseract
        with patch("shutil.which", return_value=r"C:\fake\tesseract.exe"):
            result = _find_tesseract()
            assert result == r"C:\fake\tesseract.exe"

    def test_returns_windows_path_when_which_fails(self):
        from pathlib import Path
        from aios.vision.ocr import _find_tesseract, _WINDOWS_TESSERACT_PATHS
        fake_path = _WINDOWS_TESSERACT_PATHS[0]
        real_exists = Path.exists

        def fake_exists(p):
            return p == fake_path

        with patch("shutil.which", return_value=None), \
             patch.object(Path, "exists", fake_exists):
            result = _find_tesseract()
            assert result == str(fake_path)

    def test_returns_none_when_neither_found(self):
        from aios.vision.ocr import _find_tesseract
        with patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):
            result = _find_tesseract()
            assert result is None

    def test_check_tesseract_sets_tesseract_cmd(self):
        from aios.vision import ocr as ocr_mod
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = None
        fake_exe = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
        mock_pytesseract = MagicMock()
        with patch("aios.vision.ocr._find_tesseract", return_value=fake_exe), \
             patch("pathlib.Path.exists", return_value=True), \
             patch.dict("sys.modules", {"pytesseract": mock_pytesseract}):
            result = _check_tesseract()
            assert result is True
            assert mock_pytesseract.pytesseract.tesseract_cmd == fake_exe
        mod._TESSERACT_AVAILABLE = None


class TestBundledTesseractResolution:
    """Tests for bundled Tesseract resolution (Stage 5-7 packaging)."""

    def test_bundled_dir_returns_path_when_exists(self, tmp_path):
        from aios.vision.ocr import _bundled_tesseract_dir
        tesseract_dir = tmp_path / "tesseract"
        tesseract_dir.mkdir()
        (tesseract_dir / "tesseract.exe").write_bytes(b"fake")
        with patch("aios.vision.ocr.Path") as mock_path:
            mock_python = MagicMock()
            mock_python.resolve.return_value.parent = tmp_path
            mock_path.return_value = mock_python
            result = _bundled_tesseract_dir()
        assert result == tesseract_dir

    def test_bundled_dir_returns_none_when_missing(self, tmp_path):
        from aios.vision.ocr import _bundled_tesseract_dir
        with patch("aios.vision.ocr.Path") as mock_path:
            mock_python = MagicMock()
            mock_python.resolve.return_value.parent = tmp_path
            mock_path.return_value = mock_python
            result = _bundled_tesseract_dir()
        assert result is None

    def test_find_tesseract_prefers_bundled(self, tmp_path):
        from aios.vision.ocr import _find_tesseract
        bundled_dir = tmp_path / "tesseract"
        bundled_dir.mkdir()
        bundled_exe = bundled_dir / "tesseract.exe"
        bundled_exe.write_bytes(b"fake")
        with patch("aios.vision.ocr._bundled_tesseract_dir", return_value=bundled_dir), \
             patch("shutil.which", return_value=r"C:\other\tesseract.exe"):
            result = _find_tesseract()
        assert result == str(bundled_exe)

    def test_find_tesseract_falls_to_path_when_no_bundled(self):
        from aios.vision.ocr import _find_tesseract
        with patch("aios.vision.ocr._bundled_tesseract_dir", return_value=None), \
             patch("shutil.which", return_value=r"C:\system\tesseract.exe"):
            result = _find_tesseract()
        assert result == r"C:\system\tesseract.exe"

    def test_find_tesseract_returns_none_when_all_missing(self):
        from aios.vision.ocr import _find_tesseract
        with patch("aios.vision.ocr._bundled_tesseract_dir", return_value=None), \
             patch("shutil.which", return_value=None), \
             patch("pathlib.Path.exists", return_value=False):
            result = _find_tesseract()
        assert result is None

    def test_check_tesseract_sets_tessdata_prefix_for_bundled(self, tmp_path):
        from aios.vision import ocr as ocr_mod
        import aios.vision.ocr as mod
        mod._TESSERACT_AVAILABLE = None
        bundled_dir = tmp_path / "tesseract"
        bundled_dir.mkdir()
        bundled_exe = bundled_dir / "tesseract.exe"
        bundled_exe.write_bytes(b"fake")
        tessdata = bundled_dir / "tessdata"
        tessdata.mkdir()
        mock_pytesseract = MagicMock()
        env = os.environ.copy()
        env.pop("TESSDATA_PREFIX", None)
        with patch("aios.vision.ocr._find_tesseract", return_value=str(bundled_exe)), \
             patch.dict("sys.modules", {"pytesseract": mock_pytesseract}), \
             patch.dict("os.environ", env, clear=True):
            result = _check_tesseract()
            assert result is True
            assert os.environ.get("TESSDATA_PREFIX") == str(tessdata)
        mod._TESSERACT_AVAILABLE = None

    def test_bundled_tesseract_exe_is_file(self):
        """Verify the bundled Tesseract exe exists at the expected tauri resource path."""
        import importlib.resources
        bundled = Path(__file__).resolve().parents[4] / "desktop" / "src-tauri" / "tesseract"
        # In dev, check if staging dir exists
        if bundled.is_dir():
            exe = bundled / "tesseract.exe"
            assert exe.is_file(), f"Missing bundled exe: {exe}"
