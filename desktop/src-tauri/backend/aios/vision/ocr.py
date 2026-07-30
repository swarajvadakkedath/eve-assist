"""OCR text extraction — Tesseract, EasyOCR, and mock providers."""

from io import BytesIO

from PIL import Image

from aios.vision.models import OCRResult


async def extract_text(image: Image.Image, lang: str = "eng") -> str:
    import pytesseract
    try:
        text = pytesseract.image_to_string(image, lang=lang)
        return text.strip()
    except Exception:
        return ""


async def extract_text_from_path(image_path: str, lang: str = "eng") -> str:
    image = Image.open(image_path)
    return await extract_text(image, lang)


async def extract_text_with_details(image: Image.Image, lang: str = "eng") -> OCRResult:
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
