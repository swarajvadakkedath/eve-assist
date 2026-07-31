"""Phase 4 retest: Real screen OCR via analyze-upload (after vision.py fix)."""
import http.client, time, json, sys
from PIL import Image, ImageDraw, ImageFont

PORT = 8456
HOST = "127.0.0.1"

def upload_image(img_path, filename):
    with open(img_path, "rb") as f:
        img_data = f.read()
    boundary = "----EVEBoundaryPhase4"
    parts = []
    parts.append(f'--{boundary}\r\n'.encode())
    parts.append(f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode())
    parts.append(b'Content-Type: image/png\r\n\r\n')
    parts.append(img_data)
    parts.append(f'\r\n--{boundary}--\r\n'.encode())
    body = b"".join(parts)
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Content-Length": str(len(body)),
    }
    conn = http.client.HTTPConnection(HOST, PORT, timeout=30)
    start = time.perf_counter()
    conn.request("POST", "/api/v1/vision/analyze-upload", body, headers)
    resp = conn.getresponse()
    raw = resp.read()
    latency = (time.perf_counter() - start) * 1000
    conn.close()
    return json.loads(raw), resp.status, latency

def get_latest():
    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    conn.request("GET", "/api/v1/vision/observation/latest")
    resp = conn.getresponse()
    raw = resp.read()
    conn.close()
    return json.loads(raw)

# Verify backend
try:
    conn = http.client.HTTPConnection(HOST, PORT, timeout=5)
    conn.request("GET", "/api/v1/desktop/status")
    resp = conn.getresponse()
    print(f"Backend status: {resp.status}")
    conn.close()
except Exception as e:
    print(f"Backend not running: {e}")
    sys.exit(1)

# Create image A
target_a = "EVE_OCR_RUNTIME_7429"
img_a = Image.new("RGB", (800, 120), color="white")
draw_a = ImageDraw.Draw(img_a)
try:
    font = ImageFont.truetype("arial.ttf", 48)
except Exception:
    font = ImageFont.load_default()
draw_a.text((20, 30), target_a, fill="black", font=font)
img_a_path = r"E:\Eve_Ai\sandbox\ocr_phase4a_retest.png"
img_a.save(img_a_path)

# Upload image A
data_a, status_a, latency_a = upload_image(img_a_path, "ocr_phase4a.png")
ocr_text_a = data_a.get("ocr_text", "")
pass_a = target_a in ocr_text_a
print(f"\n=== PHASE 4A: {target_a} ===")
print(f"Status: {status_a}")
print(f"ocr_text: {ocr_text_a!r}")
print(f"element_count: {data_a.get('element_count', 0)}")
print(f"observation_id: {data_a.get('observation_id', '')}")
print(f"Latency: {latency_a:.0f}ms")
print(f"PASS: {pass_a}")

# Create image B
target_b = "EVE_OCR_RUNTIME_BETA"
img_b = Image.new("RGB", (800, 120), color="white")
draw_b = ImageDraw.Draw(img_b)
draw_b.text((20, 30), target_b, fill="black", font=font)
img_b_path = r"E:\Eve_Ai\sandbox\ocr_phase4b_retest.png"
img_b.save(img_b_path)

# Upload image B
data_b, status_b, latency_b = upload_image(img_b_path, "ocr_phase4b.png")
ocr_text_b = data_b.get("ocr_text", "")
pass_b = target_b in ocr_text_b
print(f"\n=== PHASE 4B: {target_b} ===")
print(f"Status: {status_b}")
print(f"ocr_text: {ocr_text_b!r}")
print(f"observation_id: {data_b.get('observation_id', '')}")
print(f"Latency: {latency_b:.0f}ms")
print(f"PASS: {pass_b}")

# Check observation/latest is not stale
latest = get_latest()
latest_ocr = latest.get("ocr_text", "")
no_stale = target_a not in latest_ocr
print(f"\n=== OBSERVATION LATEST ===")
print(f"ocr_text: {latest_ocr!r}")
print(f"No stale 7429: {no_stale}")

overall = pass_a and pass_b and no_stale
print(f"\nPHASE 4 OVERALL: {'PASS' if overall else 'FAIL'}")
