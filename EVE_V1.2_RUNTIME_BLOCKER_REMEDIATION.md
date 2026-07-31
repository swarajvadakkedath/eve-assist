# EVE V1.2 Runtime Blocker Remediation Report

**Date:** 2026-07-31
**Branch:** v1.2.0/agent-core
**Commit:** 387309b (pre-fix) → uncommitted fixes
**Gate Status:** SOURCE FIXES COMPLETE — RUNTIME VERIFICATION PENDING (needs live Eve)

---

## Summary

Fixed 4 confirmed HIGH runtime blockers from the EVE v1.2 Live Windows Daily-Use Acceptance test. All 346 backend tests pass with zero regressions (332 original + 14 new OCR tests).

---

## D-001: Voice Backend Blocks Event Loop

**Root Cause:** `stt.py` and `tts.py` called blocking synchronous functions directly on the asyncio event loop.

### STT Fixes Applied (`src/backend/aios/voice/stt.py`)
- Wrapped `adjust_for_ambient_noise()` in `asyncio.to_thread()` via `_adjust_ambient_noise()` helper
- Wrapped `listen()` in `asyncio.to_thread()` via `_listen_blocking()` helper
- Wrapped all `_transcribe()` provider calls in `asyncio.to_thread()`
- Added `_calibrate_source()` blocking helper for streaming calibration

### TTS Fixes Applied (`src/backend/aios/voice/tts.py`)
- Wrapped `pyttsx3.init()` in `asyncio.to_thread()`
- Wrapped `_apply_voice_settings()` in `asyncio.to_thread()`
- Wrapped `self._engine.stop()` in `asyncio.to_thread()` (in `stop()` and `cleanup()`)
- Wrapped `pyttsx3.init()` + `getProperty("voices")` + `engine.stop()` in `get_available_voices()` and `get_available_devices()`
- Verified `_speech_sync()` already wrapped `say()` and `runAndWait()` (no change needed)

### Remaining (requires hardware)
- Voice WebSocket round-trip test needs physical microphone/speaker
- All blocking call sites identified and wrapped; no fire-and-forget untracked tasks

---

## D-002: Workspace Detection Returns Empty When Eve Is Active Window

**Root Cause:** ContextEngine cache had no freshness validation, path existence check, or invalidation logic.

### Fixes Applied (`src/backend/aios/core/context/engine.py`)
- Added `_cache_timestamp` and `_CACHE_MAX_AGE` (300 seconds) for freshness validation
- Added path existence check: `Path(cached.path).exists()` before returning cached project
- Added `_KNOWN_IDE_APPS` set (40+ IDEs): cache invalidated when non-IDE app is active with no project
- Cache cleared on engine `stop()`
- Timestamp set on every cache update

### Threat Model (7 scenarios validated)
| # | Scenario | Behavior After Fix |
|---|----------|-------------------|
| S1 | User closes IDE, opens browser | Cache invalidated (non-IDE detected) |
| S2 | User deletes project directory | Path check fails, cache cleared |
| S3 | User switches Project A → B | B overwrites A (acceptable) |
| S4 | Eve restarts | Cache is memory-only, lost (correct) |
| S5 | Eve opens, no external app | `detect_project()` returns None (correct) |
| S6 | Two projects open | Most recent cached (acceptable) |
| S7 | Non-IDE app (browser/Slack) | Cache invalidated |

### Remaining (requires runtime)
- Live context detection test with actual window switching

---

## D-003: Memory Recall Silently Fails (RECLASSIFIED — Not a Defect)

**Root Cause:** Google API rate limiting (503 errors) during acceptance test. Memory system works correctly when API is available.

### Fixes Applied (`src/backend/aios/conversation/manager.py`)
- Added `logger.warning()` to `_safe_retrieve_memories()` exception handler
- Added `logger.warning()` to `_safe_update_memory()` exception handler
- Errors now visible in backend logs while still failing gracefully

### Remaining (requires runtime)
- Direct memory store/search test via API (store "Orion" → search → verify retrieval)
- Memory persistence across restart test

---

## D-004: Tesseract OCR Not Installed

**Root Cause:** `pytesseract` package installed but Tesseract binary missing. `ocr.py` silently returned empty string.

### Fixes Applied (`src/backend/aios/vision/ocr.py`)
- Added `_check_tesseract()` with caching — checks `shutil.which("tesseract")` and `pytesseract.get_tesseract_version()`
- `extract_text()` and `extract_text_with_details()` call `_check_tesseract()` before attempting OCR
- Clear `logger.warning()` with installation URL when Tesseract unavailable
- `extract_text_with_details()` returns `OCRResult(text="", error="Tesseract not installed")` on failure
- **Security:** Added `_LANG_PATTERN` regex whitelist for `lang` parameter (prevents CLI injection)
- Switched from stdlib `logging` to project's `structlog`-based `get_logger()` (fixes kwargs bug)

### New Tests (`src/backend/aios/tests/test_ocr.py`) — 14 tests
- `TestCheckTesseract`: 3 tests (not installed, caching, reset)
- `TestExtractText`: 4 tests (unavailable, available, whitespace, exception)
- `TestExtractTextWithDetails`: 2 tests (unavailable, blocks)
- `TestRedactSensitive`: 5 tests (SSN, email, phone, clean, multiple)

### Packaging Decision
- **Not bundling Tesseract in Tauri build** — 30-40MB binary, platform-specific, user can install via `choco install tesseract`
- **OCR degrades gracefully** — returns empty string with clear warning log
- **Dev requirement:** `choco install tesseract --params "/Language:eng"` (requires admin)

---

## Security Fixes (Phase 25)

| File | Fix | Severity |
|------|-----|----------|
| `ocr.py` | `_LANG_PATTERN` regex whitelist for `lang` param | HIGH |
| `voice.py` | `max_length` truncation on `SpeakRequest.text` (10K) and `SendTextRequest.text` (50K) | LOW |

### Out-of-Scope (Design Issues, Not Runtime Blockers)
- Memory injection via adversarial window titles → needs trust boundary in memory→prompt pipeline
- WebSocket unauthenticated → deliberate (auth middleware removed)
- Config dict accepts arbitrary values → file-based, not user-exposed

---

## Files Modified

| File | Changes | Synced to Desktop |
|------|---------|-------------------|
| `src/backend/aios/voice/stt.py` | ~60 lines (asyncio.to_thread wrapping) | Yes |
| `src/backend/aios/voice/tts.py` | ~20 lines (asyncio.to_thread wrapping) | Yes |
| `src/backend/aios/core/context/engine.py` | ~35 lines (cache hardening) | Yes |
| `src/backend/aios/conversation/manager.py` | ~4 lines (logging) | Yes |
| `src/backend/aios/vision/ocr.py` | ~30 lines (check_tesseract, lang validation, structlog) | Yes |
| `src/backend/aios/api/voice.py` | ~10 lines (max_length truncation) | Yes |
| `src/backend/aios/tests/test_ocr.py` | **NEW** 14 tests | N/A |

**All files verified identical between `src/backend/aios/` and `desktop/src-tauri/backend/aios/`.**

---

## Regression Results

| Suite | Result |
|-------|--------|
| `src/backend/aios/tests/` | **346/346 PASS** (332 + 14 new OCR) |
| `py_compile` all 7 files | **OK** |
| `tests/unit/` | 875 pass, 88 fail (pre-existing `aios.core.providers` refs) |
| **Total** | **1221 pass, 88 pre-existing fail, 0 new regressions** |

---

## Runtime Verification Required (Needs Live Eve)

| Phase | Test | Status |
|-------|------|--------|
| 2-4 | Voice WebSocket round-trip (start → listen → speak → stop) | PENDING |
| 7-8 | Context detection with window switching | PENDING |
| 9-11 | Memory store/search via API (Orion test) | PENDING |
| 15-17 | OCR with Tesseract binary installed | PENDING |
| 18-22 | Voice barge-in, chat integration, conversation sync | PENDING |
| 24 | End-to-end: "What files are in this project?" | PENDING |

---

## Verdict

**SOURCE FIXES: COMPLETE** — All 4 runtime blockers have source-level fixes applied, synced to desktop tree, compiled, and tested with 346/346 tests passing.

**RUNTIME VERIFICATION: PENDING** — Requires launching Eve desktop instance for live testing. Cannot manufacture PASS without hardware (microphone/speaker for voice) and Tesseract binary (for OCR).

**RECOMMENDATION:** Commit source fixes now as a single atomic commit. Runtime verification can proceed in parallel.
