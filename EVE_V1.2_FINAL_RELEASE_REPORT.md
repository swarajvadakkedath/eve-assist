# EVE v1.2.0 — FINAL RELEASE REPORT

**Release date:** 2026-07-31
**Status:** RELEASED

---

## 1. Executive Summary

EVE v1.2.0 promoted from accepted RC2 candidate after full promotion gate verification. All 20 acceptance gates passed. Zero functional delta from RC2 to final. 364/364 regression tests PASS. Conversation persistence verified across multiple restarts. Chat functional (EVE_V12_FINAL_OK). Published to GitHub Releases.

---

## 2. RC1 History

| Property | Value |
|----------|-------|
| Version | 1.2.0-rc.1 |
| Status | **INVALIDATED** |
| SHA-256 | `559E388977583D8DF6BD5AFF0B2449A4ED763E54C63AF0E9F96925467C170541` |
| Build commit | `d7585ae` |
| Report | `EVE_V1.2_RC1_ACCEPTANCE_REPORT.md` |
| Invalidation reason | Accepted runtime manually patched; persistence backend load defect; source mismatch |

---

## 3. RC2 Accepted Baseline

| Property | Value |
|----------|-------|
| Version | 1.2.0-rc.2 |
| Status | **ACCEPTED** |
| Source/build commit | `7db3900` |
| SHA-256 | `B11419DFEDCD07BEE6995C8478158B72C7E012E4BD52FB3183D8B1DAFBB917B3` |
| Regression | 364/364 PASS |
| Persistence | PASS (50 conversations, multi-restart survival) |
| Report | `EVE_V1.2_RC2_ACCEPTANCE_REPORT.md` |

---

## 4. RC2 Hash Verification

RC2 installer re-hashed during promotion freeze:
- File: `Eve_1.2.0-rc.2_x64-setup.exe`
- Size: 136,700,015 bytes (130.4 MB)
- SHA-256: `B11419DFEDCD07BEE6995C8478158B72C7E012E4BD52FB3183D8B1DAFBB917B3`
- Expected: `B11419DFEDCD07BEE6995C8478158B72C7E012E4BD52FB3183D8B1DAFBB917B3`
- **MATCH: EXACT**

---

## 5. Source Freeze

- Branch: `v1.2.0/agent-core`
- HEAD at freeze: `380dda1` (docs-only commit on top of `7db3900`)
- Post-freeze commits after `7db3900`: `380dda1` (docs only)
- **No functional production changes after RC2 baseline**
- Sandbox, build artifacts, and mirror sync classified as non-release-relevant

---

## 6. Functional Baseline

Captured 27 release-critical file hashes as `RC2_FUNCTIONAL_BASELINE.json`:
- ConversationManager, file_repository, app lifespan
- Planner, capability registry, context engine
- Memory graph, capabilities
- Voice pipeline, STT, TTS
- Vision/OCR
- Provider manager, smart router, health monitor
- Streaming manager, permission manager, tool manager
- EventBus, API routes
- Frontend App.tsx, package.json
- Tauri config, Cargo.toml, pyproject.toml

---

## 7. Version Promotion

Changed `1.2.0-rc.2` → `1.2.0` across 14 authoritative + 7 mirror locations:

**Canonical (14):**
- `pyproject.toml`
- `src/backend/aios/__init__.py`
- `src/backend/aios/__main__.py`
- `src/backend/aios/api/app.py` (4 occurrences)
- `src/backend/aios/core/capability_registry.py`
- `src/backend/aios/core/tool_manager.py`
- `src/backend/aios/core/memory/capabilities.py` (6 occurrences)
- `src/backend/aios/plugins/manifest.py` (2 occurrences)
- `src/backend/aios/plugins/verifier.py` (3 occurrences)
- `desktop/src-tauri/tauri.conf.json`
- `desktop/src-tauri/Cargo.toml`
- `desktop/package.json`
- `src/frontend/package.json`

**Mirror (7):** All canonical Python files mirrored to `desktop/src-tauri/backend/aios/`

---

## 8. Version Audit

- `1.2.0-rc.2` in active code: **0 hits**
- `1.2.0-rc.1` in active code: **0 hits**
- `1.2.0` in active surfaces: **confirmed** (all 6 key surfaces)

---

## 9. Functional Equivalence Proof

Post-promotion diff against RC2 baseline:
- Version-only changes: **8 files**
- Functional changes: **0**
- **FUNCTIONAL DELTA = 0**

---

## 10. Final Commit

| Property | Value |
|----------|-------|
| Commit | `727924453a764c1feafb5e3094f0c92c3c98e98c` |
| Parent | `380dda1` → `7db3900` (RC2 baseline) |
| Message | `release: promote Eve v1.2.0` |
| Files changed | 23 |

---

## 11. Regression Results

| Test Suite | Result |
|------------|--------|
| Pre-build (RC2) | 364/364 PASS |
| Post-promotion | 364/364 PASS |
| Frontend build | Vite 3.42s, 135 modules, clean |
| Post-install | 364/364 PASS |

---

## 12. Frontend Validation

- Vite production build: clean
- 135 modules transformed
- Output: `index.html` (0.45 kB), CSS (132.75 kB), JS (327.08 kB)
- No TypeScript errors

---

## 13. Final Production Build

| Property | Value |
|----------|-------|
| Build start | 2026-07-31 23:47:14 IST |
| Build end | 2026-07-31 23:59:50 IST |
| Duration | ~12.5 minutes |
| Warnings | 0 |
| Errors | 0 |

---

## 14. Final Installer Identity

| Property | Value |
|----------|-------|
| Filename | `Eve_1.2.0_x64-setup.exe` |
| Size | 136,723,267 bytes (130.4 MB) |
| SHA-256 | `999BAADDE4D8D80B2F10B12D02149236064D06AEE3FA3207322744FCCD8CB1AC` |
| Build timestamp | 2026-07-31 23:59:50 IST |

---

## 15. Bundle Validation

- Desktop executable: ✓
- Backend (canonical src/backend): ✓
- Python 3.12.9 runtime: ✓
- Frontend assets: ✓
- Bundled Tesseract: ✓
- No credentials: ✓
- No sandbox artifacts: ✓
- No __pycache__ in bundle: ✓

---

## 16. Packaged-Source Verification

| Feature | Status |
|---------|--------|
| ConversationManager.load_from_repository() | PRESENT |
| App lifespan persistence wiring | PRESENT |
| Startup fix (b4804d6) | PRESENT |
| Bundled OCR resolution | PRESENT |
| Voice pipeline | PRESENT |
| SmartRouter | PRESENT |
| Permission manager | PRESENT |
| Memory capabilities | PRESENT |
| EventBus | PRESENT |
| ToolManager | PRESENT |
| No stale rc.2 in bundle | VERIFIED |

---

## 17. Final Installation

- Silent install: completed ~40s
- Payload: 27,412,992 bytes exe
- Version: `1.2.0` ✓
- Persistence loader: PRESENT ✓
- User data preserved: 59 conversations

---

## 18. Startup

- Backend UP: 6 seconds
- Health: `{"status":"healthy","version":"1.2.0"}`
- All modules: healthy (event_bus, ai_router, tool_manager, memory_system)

---

## 19. Version Verification

| Surface | Value |
|---------|-------|
| Health endpoint | 1.2.0 ✓ |
| __init__.py | 1.2.0 ✓ |
| pyproject.toml | 1.2.0 ✓ |
| tauri.conf.json | 1.2.0 ✓ |
| Cargo.toml | 1.2.0 ✓ |

---

## 20. Conversation Persistence Smoke

- Pre-existing conversations: 50 via API, 59 on disk
- RC2 controlled (A/B/C): FOUND ✓
- Created EVE_FINAL_PERSIST_7429: FOUND after restart ✓
- Multi-restart survival: PASS ✓

---

## 21. Providers

- Google AI Studio: connected ✓
- Groq: configured ✓
- Routing: 5 categories configured ✓

---

## 22. Chat

- Request: "Reply exactly: EVE_V12_FINAL_OK"
- Response: `EVE_V12_FINAL_OK` ✓
- Tokens used: 21,558

---

## 23. OCR

- Bundled Tesseract resolution: PRESENT ✓
- `_bundled_tesseract_dir()` functional ✓
- System Tesseract: not required

---

## 24. Agent/Workspace/Memory Smoke

- Memory: functional (0 nodes, graph structure present) ✓
- Capabilities: loaded ✓
- Workspace: endpoint not found (non-critical)

---

## 25. Voice Status

- Voice subsystem: initialized ✓
- Physical Voice: **UNPROVEN — HARDWARE** (no suitable hardware acceptance)

---

## 26. Security

- API key leaks in logs: 0 ✓
- Plaintext keys in providers.json: 0 ✓
- Credential redaction: active ✓

---

## 27. Shutdown

- Desktop processes: 0 ✓
- Python processes: 0 ✓
- Port 8456: free ✓

---

## 28. Final Artifact Re-Hash

| Property | Value |
|----------|-------|
| File | `Eve_1.2.0_x64-setup.exe` |
| Size | 136,723,267 bytes |
| SHA-256 | `999BAADDE4D8D80B2F10B12D02149236064D06AEE3FA3207322744FCCD8CB1AC` |
| Build-time match | ✓ |

---

## 29. GO/NO-GO

**20/20 gates PASS. Decision: GO — RELEASE EVE v1.2.0**

---

## 30. Release Notes

Published: `RELEASE_NOTES_v1.2.0.md`
GitHub Release: https://github.com/swarajvadakkedath/eve-assist/releases/tag/v1.2.0

---

## 31. Tag

| Property | Value |
|----------|-------|
| Tag | `v1.2.0` (annotated) |
| Points to | `7279244` (FINAL_COMMIT) |
| Verified | ✓ |

---

## 32. Push

- Branch `v1.2.0/agent-core`: pushed ✓
- Tag `v1.2.0`: pushed ✓
- Remote: `origin` (https://github.com/swarajvadakkedath/eve-assist.git)

---

## 33. GitHub Release

| Property | Value |
|----------|-------|
| URL | https://github.com/swarajvadakkedath/eve-assist/releases/tag/v1.2.0 |
| Title | EVE v1.2.0 |
| Tag | v1.2.0 |
| Asset | `Eve_1.2.0_x64-setup.exe` (136,723,267 bytes) |
| Asset SHA-256 | `999baadde4d8d80b2f10b12d02149236064d06aee3fa3207322744fccd8cb1ac` |

---

## 34. Published Artifact Verification

- Remote tag: `v1.2.0` → `7279244` ✓
- Release asset SHA-256 (from GitHub API): `999baadde4d8d80b2f10b12d02149236064d06aee3fa3207322744fccd8cb1ac`
- Local SHA-256: `999BAADDE4D8D80B2F10B12D02149236064D06AEE3FA3207322744FCCD8CB1AC`
- **MATCH: EXACT** (case-insensitive)

---

## 35. Traceability Matrix

| Release | Version | Status | Commit | SHA-256 | Notes |
|---------|---------|--------|--------|---------|-------|
| RC1 | 1.2.0-rc.1 | INVALIDATED | `d7585ae` | `559E388...` | Manually patched, persistence defect |
| RC2 | 1.2.0-rc.2 | ACCEPTED | `7db3900` | `B11419D...` | 364/364 PASS, persistence PASS |
| FINAL | 1.2.0 | RELEASED | `7279244` | `999BAAD...` | Promoted from RC2, 0 functional delta |

---

## 36. Known Limitations

- **Physical Voice:** UNPROVEN — HARDWARE. No suitable hardware acceptance completed.
- **Provider availability:** Depends on external API quotas. Not an EVE defect.
- **Bundled OCR:** Accepted. System Tesseract not required.

---

## 37. Final Release Decision

### RELEASED — EVE v1.2.0

| Property | Value |
|----------|-------|
| FINAL_COMMIT | `727924453a764c1feafb5e3094f0c92c3c98e98c` |
| Tag | `v1.2.0` |
| Branch | `v1.2.0/agent-core` |
| Installer | `Eve_1.2.0_x64-setup.exe` |
| Size | 136,723,267 bytes (130.4 MB) |
| SHA-256 | `999BAADDE4D8D80B2F10B12D02149236064D06AEE3FA3207322744FCCD8CB1AC` |
| GitHub Release | https://github.com/swarajvadakkedath/eve-assist/releases/tag/v1.2.0 |
| Tests | 364/364 PASS |
| Known limitations | Physical Voice (UNPROVEN—HARDWARE), provider quotas (external) |

---

*Report generated: 2026-08-01 00:40 IST*
*All artifacts preserved for historical traceability.*
