import sys, time, asyncio, json, http.client
sys.path.insert(0, r"E:\Eve_Ai\src\backend")

from PIL import Image, ImageDraw, ImageFont

# Create image with second marker (not the direct test one)
target = "EVE_OCR_RUNTIME_7429"
img = Image.new("RGB", (800, 120), color="white")
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("arial.ttf", 48)
except:
    font = ImageFont.load_default()
draw.text((20, 30), target, fill="black", font=font)
img.save(r"E:\Eve_Ai\sandbox\ocr_runtime_test.png")

# Test 1: Direct OCR via EVE module (bypasses backend cache)
from aios.vision import ocr as ocr_mod
ocr_mod._TESSERACT_AVAILABLE = None  # Reset cache
from aios.vision.ocr import extract_text_with_details
start = time.perf_counter()
result = asyncio.run(extract_text_with_details(img, lang="eng"))
latency = (time.perf_counter() - start) * 1000
print(f"Direct OCR: text='{result.text}', confidence={result.confidence:.2f}, latency={latency:.0f}ms")
if target in result.text:
    print("Direct OCR: PASS")
else:
    print(f"Direct OCR: FAIL (expected '{target}')")

# Test 2: Via vision API after backend restart
print("\nAttempting vision API...")
try:
    with open(r"E:\Eve_Ai\sandbox\ocr_runtime_test.png", "rb") as f:
        img_data = f.read()
    
    conn = http.client.HTTPConnection("127.0.0.1", 8456, timeout=30)
    boundary = "----EVEBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="ocr_test.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + img_data + f"\r\n--{boundary}--\r\n".encode()
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body))
    }
    start = time.perf_counter()
    conn.request("POST", "/api/v1/vision/analyze-upload", body, headers)
    resp = conn.getresponse()
    data = json.loads(resp.read())
    latency = (time.perf_counter() - start) * 1000
    conn.close()
    
    ocr_text = data.get("ocr_text", "")
    print(f"Vision API: ocr_text='{ocr_text}', latency={latency:.0f}ms")
    if target in ocr_text:
        print("Vision API OCR: PASS")
    else:
        print(f"Vision API OCR: FAIL (ocr_text empty, backend needs restart)")
except Exception as e:
    print(f"Vision API error: {e}")
