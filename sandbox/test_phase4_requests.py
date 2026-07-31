import requests, time

target = "EVE_OCR_RUNTIME_7429"
url = "http://127.0.0.1:8456/api/v1/vision/analyze-upload"

with open(r"E:\Eve_Ai\sandbox\ocr_phase4a.png", "rb") as f:
    start = time.perf_counter()
    resp = requests.post(url, files={"file": ("test.png", f, "image/png")}, timeout=30)
    latency = (time.perf_counter() - start) * 1000

print(f"Status: {resp.status_code}")
print(f"Latency: {latency:.0f}ms")
data = resp.json()
print(f"ocr_text: '{data.get('ocr_text', '')}'")
print(f"element_count: {data.get('element_count', 0)}")
print(f"summary: {data.get('summary', '')}")

if target in data.get("ocr_text", ""):
    print("\nPHASE 4: PASS")
else:
    print(f"\nPHASE 4: OCR text empty, checking if file was received...")
    # Try with explicit content type
    with open(r"E:\Eve_Ai\sandbox\ocr_phase4a.png", "rb") as f2:
        img_bytes = f2.read()
    print(f"File size: {len(img_bytes)} bytes")
    print(f"First 16 bytes: {img_bytes[:16]}")
