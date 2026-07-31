"""Phase 17: Final restart verification."""
import http.client, json, sys, os
from PIL import Image, ImageDraw, ImageFont

HOST, PORT = "127.0.0.1", 8456

def api_get(path):
    conn = http.client.HTTPConnection(HOST, PORT, timeout=10)
    conn.request("GET", path)
    r = conn.getresponse()
    data = r.read().decode()
    conn.close()
    return r.status, data

print("=== PHASE 17: FINAL RESTART VERIFICATION ===\n")

# [1] Ready
status, body = api_get("/api/v1/desktop/status")
data = json.loads(body)
print(f"[1] Status: {status} - {data.get('status', '')}")

# [2] Providers
status, body = api_get("/api/v1/providers")
data = json.loads(body)
providers = data if isinstance(data, list) else data.get("providers", [])
print(f"[2] Providers: {status} - {len(providers)} providers")
for p in providers:
    print(f"    - {p.get('name', '?')} (enabled: {p.get('enabled', '?')})")

# [3] Settings
status, body = api_get("/api/v1/desktop/settings")
data = json.loads(body)
keys = list(data.keys())[:8]
print(f"[3] Settings: {status} - keys: {keys}")

# [4] OCR available
sys.path.insert(0, r"E:\Eve_Ai\src\backend")
from aios.vision.ocr import _check_tesseract
ocr_avail = _check_tesseract()
print(f"[4] OCR available: {ocr_avail}")

# [5] One OCR request
target = "EVE_RESTART_VERIFY_3821"
img = Image.new("RGB", (600, 80), color="white")
draw = ImageDraw.Draw(img)
try:
    font = ImageFont.truetype("arial.ttf", 36)
except Exception:
    font = ImageFont.load_default()
draw.text((20, 20), target, fill="black", font=font)
img_path = r"E:\Eve_Ai\sandbox\restart_verify.png"
img.save(img_path)

with open(img_path, "rb") as f:
    img_data = f.read()
boundary = "----EVERestart"
parts = []
parts.append(f"--{boundary}\r\n".encode())
parts.append(b'Content-Disposition: form-data; name="file"; filename="test.png"\r\n')
parts.append(b"Content-Type: image/png\r\n\r\n")
parts.append(img_data)
parts.append(f"\r\n--{boundary}--\r\n".encode())
body = b"".join(parts)
headers = {"Content-Type": f"multipart/form-data; boundary={boundary}", "Content-Length": str(len(body))}
conn = http.client.HTTPConnection(HOST, PORT, timeout=30)
conn.request("POST", "/api/v1/vision/analyze-upload", body, headers)
resp = conn.getresponse()
raw = resp.read()
conn.close()
data = json.loads(raw)
ocr_text = data.get("ocr_text", "")
ocr_pass = target in ocr_text
print(f"[5] OCR after restart: '{ocr_text}' - PASS: {ocr_pass}")

# [6] Voice state
try:
    status, body = api_get("/api/v1/voice/state")
    print(f"[6] Voice state: {status} - {body[:200]}")
except Exception as e:
    print(f"[6] Voice state: ERROR - {e}")

# [7] Final health
status, body = api_get("/api/v1/desktop/status")
print(f"[7] Final health: {status}")

overall = status == 200 and ocr_pass
print(f"\n=== PHASE 17 OVERALL: {'PASS' if overall else 'FAIL'} ===")
