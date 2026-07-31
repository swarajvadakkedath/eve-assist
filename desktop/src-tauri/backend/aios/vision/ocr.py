"""OCR text extraction — Tesseract, EasyOCR, and mock providers."""

import os
import re
import sys
from io import BytesIO
from pathlib import Path
import shutil

from PIL import Image

from aios.vision.models import OCRResult
from aios.utils.logger import get_logger

logger = get_logger(__name__)

_TESSERACT_AVAILABLE: bool | None = None
_LANG_PATTERN = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z]+)*$")
_WINDOWS_TESSERACT_PATHS = [
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "Tesseract-OCR" / "tesseract.exe",
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")) / "Tesseract-OCR" / "tesseract.exe",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Tesseract-OCR" / "tesseract.exe",
    Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "chocolatey" / "bin" / "tesseract.exe",
]


def _bundled_tesseract_dir() -> Path | None:
    """Resolve the bundled Tesseract directory relative to the Python executable."""
    try:
        python_dir = Path(sys.executable).resolve().parent
        candidate = python_dir / "tesseract"
        if (candidate / "tesseract.exe").is_file():
            return candidate
    except Exception:
        pass
    return None


def _find_tesseract() -> str | None:
    """Find tesseract executable via bundled, PATH, or common Windows locations."""
    bundled = _bundled_tesseract_dir()
    if bundled:
        return str(bundled / "tesseract.exe")
    exe = shutil.which("tesseract")
    if exe:
        return exe
    for path in _WINDOWS_TESSERACT_PATHS:
        if path.exists():
            return str(path)
    return None


def _check_tesseract() -> bool:
    global _TESSERACT_AVAILABLE
    if _TESSERACT_AVAILABLE is not None:
        return _TESSERACT_AVAILABLE
    try:
        import pytesseract
        exe = _find_tesseract()
        if exe:
            pytesseract.pytesseract.tesseract_cmd = exe
            tessdata = str(Path(exe).parent / "tessdata")
            if Path(tessdata).exists():
                os.environ.setdefault("TESSDATA_PREFIX", tessdata)
            _TESSERACT_AVAILABLE = True
        else:
            pytesseract.get_tesseract_version()
            _TESSERACT_AVAILABLE = True
    except Exception:
        _TESSERACT_AVAILABLE = False
        logger.warning(
            "ocr.tesseract_unavailable",
            hint="Install Tesseract: https://github.com/UB-Mannheim/tesseract/wiki",
        )
    return _TESSERACT_AVAILABLE


async def extract_text(image: Image.Image, lang: str = "eng") -> str:
    if not _LANG_PATTERN.match(lang):
        logger.warning("ocr.invalid_lang", lang=lang)
        return ""
    if not _check_tesseract():
        return ""
    import pytesseract
    try:
        text = pytesseract.image_to_string(image, lang=lang)
        return text.strip()
    except Exception as e:
        logger.warning("ocr.extract_text_failed", error=str(e)[:200])
        return ""


async def extract_text_from_path(image_path: str, lang: str = "eng") -> str:
    image = Image.open(image_path)
    return await extract_text(image, lang)


async def extract_text_with_details(image: Image.Image, lang: str = "eng") -> OCRResult:
    if not _LANG_PATTERN.match(lang):
        return OCRResult(text="", error=f"Invalid language code: {lang}")
    if not _check_tesseract():
        return OCRResult(text="", error="Tesseract not installed")
    import pytesseract
    try:
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        text = " ".join([t for t in data["text"] if t.strip()])
        confidences = [int(c) for i, c in enumerate(data["conf"]) if data["text"][i].strip() and c != "-1"]
        avg_conf = (sum(confidences) / len(confidences) / 100.0) if confidences else 0.0
        blocks = []
        for i in range(len(data["text"])):
            if data["text"][i].strip():
                blocks.append({
                    "text": data["text"][i],
                    "conf": int(data["conf"][i]) if data["conf"][i] != "-1" else 0,
                    "x": data["left"][i],
                    "y": data["top"][i],
                    "w": data["width"][i],
                    "h": data["height"][i],
                })
        return OCRResult(text=text, confidence=avg_conf, language=lang, blocks=blocks)
    except Exception as e:
        return OCRResult(text="", error=str(e))


async def extract_text_from_bytes(image_data: bytes, lang: str = "eng") -> OCRResult:
    img = Image.open(BytesIO(image_data))
    return await extract_text_with_details(img, lang)


async def redact_sensitive(text: str) -> str:
    import re
    patterns = [
        (r'\b\d{3}-\d{2}-\d{4}\b', '[REDACTED-SSN]'),
        (r'\b\d{16}\b', '[REDACTED-CC]'),
        (r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b', '[REDACTED-PHONE]'),
        (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', '[REDACTED-EMAIL]'),
        (r'\b[A-Z]{2}\d{6}\b', '[REDACTED-ID]'),
        (r'\b\d{5}(-\d{4})?\b', '[REDACTED-ZIP]'),
    ]
    result = text
    for pattern, replacement in patterns:
        result = re.sub(pattern, replacement, result)
    return result
