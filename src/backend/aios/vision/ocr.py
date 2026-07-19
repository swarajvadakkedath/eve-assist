"""OCR text extraction using Tesseract."""

from PIL import Image


async def extract_text(image: Image.Image, lang: str = "eng") -> str:
    import pytesseract
    try:
        text = pytesseract.image_to_string(image, lang=lang)
        return text.strip()
    except Exception as e:
        return f""

async def extract_text_from_path(image_path: str, lang: str = "eng") -> str:
    image = Image.open(image_path)
    return await extract_text(image, lang)
