import json, http.client, time

def api_get(path):
    conn = http.client.HTTPConnection("127.0.0.1", 8456, timeout=5)
    conn.request("GET", path)
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return json.loads(data), resp.status

def api_post_multipart(path, img_path):
    with open(img_path, "rb") as f:
        img_data = f.read()
    conn = http.client.HTTPConnection("127.0.0.1", 8456, timeout=30)
    boundary = "----EVEBoundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="test.png"\r\n'
        f"Content-Type: image/png\r\n\r\n"
    ).encode() + img_data + f"\r\n--{boundary}--\r\n".encode()
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(body))}
    start = time.perf_counter()
    conn.request("POST", path, body, headers)
    resp = conn.getresponse()
    data = json.loads(resp.read())
    latency = (time.perf_counter() - start) * 1000
    conn.close()
    return data, resp.status, latency

from PIL import Image, ImageDraw, ImageFont

def create_image(text, path):
    img = Image.new("RGB", (900, 120), color="white")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 52)
    except:
        font = ImageFont.load_default()
    draw.text((20, 30), text, fill="black", font=font)
    img.save(path)
    return path

print("=== PHASE 4: REAL SCREEN OCR ===")

# Test 1: EVE_OCR_RUNTIME_7429
target1 = "EVE_OCR_RUNTIME_7429"
img1 = create_image(target1, r"E:\Eve_Ai\sandbox\ocr_phase4a.png")
data1, status1, lat1 = api_post_multipart("/api/v1/vision/analyze-upload", img1)
ocr1 = data1.get("ocr_text", "")
print(f"Test 1: target='{target1}', ocr='{ocr1}', status={status1}, latency={lat1:.0f}ms")
pass1 = target1 in ocr1
print(f"  Result: {'PASS' if pass1 else 'FAIL'}")

# Test 2: EVE_OCR_RUNTIME_BETA (staleness check)
target2 = "EVE_OCR_RUNTIME_BETA"
img2 = create_image(target2, r"E:\Eve_Ai\sandbox\ocr_phase4b.png")
data2, status2, lat2 = api_post_multipart("/api/v1/vision/analyze-upload", img2)
ocr2 = data2.get("ocr_text", "")
print(f"\nTest 2: target='{target2}', ocr='{ocr2}', status={status2}, latency={lat2:.0f}ms")
pass2 = target2 in ocr2 and "7429" not in ocr2
print(f"  Result: {'PASS' if pass2 else 'FAIL'}")

# Test 3: Verify no stale 7429
print(f"\nStaleness check: '7429' in test 2 OCR: {'7429' in ocr2}")
no_stale = "7429" not in ocr2
print(f"  No stale: {'PASS' if no_stale else 'FAIL'}")

# Observation latest check
obs, _ = api_get("/api/v1/vision/observation/latest")
print(f"\nLatest observation OCR: '{obs.get('ocr_text', '')[:100]}'")

if pass1 and pass2 and no_stale:
    print("\n=== PHASE 4: PASS ===")
else:
    print("\n=== PHASE 4: PARTIAL ===")
