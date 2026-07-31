import sys, time, asyncio
sys.path.insert(0, r"E:\Eve_Ai\src\backend")

from PIL import Image, ImageDraw, ImageFont

# Generate test image with known text
def create_test_image(text, filename):
    img = Image.new("RGB", (800, 120), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 48)
    except:
        font = ImageFont.load_default()
    draw.text((20, 30), text, fill="black", font=font)
    img.save(filename)
    return filename

print("=== PHASE 3: DIRECT OCR SANITY ===")

# Create image with target text
target = "EVE_OCR_DIRECT_7429"
img_path = create_test_image(target, r"E:\Eve_Ai\sandbox\ocr_test.png")
print(f"Created test image: {img_path}")

# Run OCR through EVE's OCR module
from aios.vision.ocr import extract_text, extract_text_with_details, _check_tesseract

print(f"Tesseract available: {_check_tesseract()}")

start = time.perf_counter()
img = Image.open(img_path)
result_text = asyncio.run(extract_text(img, lang="eng"))
ocr_latency = (time.perf_counter() - start) * 1000

print(f"OCR result: '{result_text}'")
print(f"OCR latency: {ocr_latency:.0f}ms")

if target in result_text:
    print("DIRECT OCR: PASS")
else:
    print(f"DIRECT OCR: FAIL (expected '{target}', got '{result_text}')")
    # Try with details
    start2 = time.perf_counter()
    details = asyncio.run(extract_text_with_details(img, lang="eng"))
    detail_latency = (time.perf_counter() - start2) * 1000
    print(f"Details: text='{details.text}', confidence={details.confidence}, blocks={len(details.blocks)}")
    print(f"Detail latency: {detail_latency:.0f}ms")

print("\n=== PHASE 3: COMPLETE ===")
