import http.client, time, json

target = "EVE_OCR_RUNTIME_7429"
img_path = r"E:\Eve_Ai\sandbox\ocr_phase4a.png"

with open(img_path, "rb") as f:
    img_data = f.read()

print(f"Image size: {len(img_data)} bytes")
print(f"First 8 bytes hex: {img_data[:8].hex()}")

# Use http.client with proper multipart
conn = http.client.HTTPConnection("127.0.0.1", 8456, timeout=30)
boundary = "----EVEBoundary123"

# Build multipart body properly
parts = []
parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"test.png\"\r\nContent-Type: image/png\r\n\r\n".encode())
parts.append(img_data)
parts.append(f"\r\n--{boundary}--\r\n".encode())
body = b"".join(parts)

headers = {
    "Content-Type": f"multipart/form-data; boundary={boundary}",
    "Content-Length": str(len(body))
}

start = time.perf_counter()
conn.request("POST", "/api/v1/vision/analyze-upload", body, headers)
resp = conn.getresponse()
raw = resp.read()
latency = (time.perf_counter() - start) * 1000
conn.close()

print(f"Status: {resp.status}")
print(f"Latency: {latency:.0f}ms")

try:
    data = json.loads(raw)
    ocr_text = data.get("ocr_text", "")
    print(f"ocr_text: '{ocr_text}'")
    print(f"element_count: {data.get('element_count', 0)}")
    print(f"summary: {data.get('summary', '')[:200]}")
    print(f"observation_id: {data.get('observation_id', '')}")
    
    if target in ocr_text:
        print("\nPHASE 4 SCREEN OCR: PASS")
    else:
        print(f"\nPHASE 4: OCR text empty or mismatch")
except Exception as e:
    print(f"Parse error: {e}")
    print(f"Raw response: {raw[:300]}")
