import sys, asyncio
sys.path.insert(0, r"E:\Eve_Ai\src\backend")
from aios.vision.engine import VisionEngine
from aios.vision.models import VisionConfig

engine = VisionEngine(VisionConfig())

with open(r"E:\Eve_Ai\sandbox\ocr_phase4a.png", "rb") as f:
    img_data = f.read()

print(f"Image bytes: {len(img_data)}")
result = asyncio.run(engine.ocr_image_from_bytes(img_data))
print(f"OCR text: '{result.text}'")
print(f"Confidence: {result.confidence}")
print(f"Error: {result.error}")
