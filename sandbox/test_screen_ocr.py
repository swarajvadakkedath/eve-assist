import json, http.client, time

with open(r"E:\Eve_Ai\sandbox\ocr_test.png", "rb") as f:
    img_data = f.read()

print(f"Image size: {len(img_data)} bytes")

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

print(f"Status: {resp.status}")
print(f"Latency: {latency:.0f}ms")
print(f"Response: {json.dumps(data, indent=2)[:600]}")

# Check if OCR text contains target
text = str(data)
if "EVE_OCR_DIRECT_7429" in text:
    print("\nSCREEN OCR: PASS")
else:
    print(f"\nSCREEN OCR: target not found in response")
