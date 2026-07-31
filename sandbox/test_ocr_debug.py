import sys, asyncio
sys.path.insert(0, r"E:\Eve_Ai\src\backend")
from aios.vision.ocr import extract_text_from_bytes, _check_tesseract

print("Tesseract available:", _check_tesseract())

with open(r"E:\Eve_Ai\sandbox\ocr_phase4a.png", "rb") as f:
    img_data = f.read()

print(f"Image bytes: {len(img_data)}")
result = asyncio.run(extract_text_from_bytes(img_data, lang="eng"))
print(f"OCR text: '{result.text}'")
print(f"Confidence: {result.confidence}")
print(f"Blocks: {len(result.blocks)}")
print(f"Error: {result.error}")
