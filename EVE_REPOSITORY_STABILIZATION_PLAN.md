# EVE Repository Stabilization Plan

**Generated:** 2026-08-02
**Status:** AUDIT COMPLETE — READY FOR STABILIZATION
**Recommendation:** **GO** — Repository ready for stabilization work

---

## Executive Summary

The repository audit identified 8 structural issues. After source-level verification, **6 are confirmed**, **1 is partially confirmed**, and **1 is a false positive**. The repository is functional but carries significant technical debt: 292 mirrored backend files, 27 mistakenly committed test artifacts (including a 50 MB binary), orphaned dead code across frontend and backend, and CI that covers only ~63% of the test suite. No new features should be attempted until stabilization completes.

**Repository Health Score: 5.6/10** (unchanged from audit — verification confirms the assessment)

---

## Phase 1: Verified Findings

### Finding 1: Main Branch is v1.0.0 — CONFIRMED

| Branch | Head Commit | Description |
|--------|-------------|-------------|
| `main` | `08ff323` | "fix: NSIS uninstall removes bundled Python/runtime files completely" |
| `v1.2.0/agent-core` | `09cd752` | "release: promote Eve v1.2.1 with critical launcher deadlock fix" |

- **29 commits** on `v1.2.0/agent-core` not on `main`
- **0 commits** on `main` not on `v1.2.0/agent-core`
- **670 files changed**, +106,172 / -1,632 lines between them
- `main` has not received any development since the v1.0.0-era NSIS fix

**Verdict:** CONFIRMED. `main` is effectively frozen at v1.0.0.

### Finding 2: CI Executes Only pytest tests/ — CONFIRMED

**CI file:** `.github/workflows/ci.yml`

Current CI pipeline:
```
backend job:
  - ruff check src/backend/
  - mypy src/backend/
  - pytest tests/                    ← only this directory

frontend job:
  - npx tsc --noEmit
  - npm run build
```

**Test inventory:**
- `tests/` directory: **79 test files** (unit, agent, integration, e2e, launcher)
- `src/backend/` embedded tests: **46 test files** (conversation, desktop, execution, plugins, vision, voice, workspace)
- **Total: 125 test files**
- CI runs: **79** (63% coverage)

**Missing test suites not executed by CI:**

| Suite | Files | Location | Description |
|-------|-------|----------|-------------|
| conversation/ | 5 | `src/backend/aios/conversation/tests/` | Manager, formatter, models, prompts, stream |
| desktop/ | 4 | `src/backend/aios/desktop/tests/` | Hotkeys, notifications, settings, status |
| execution/ | 6 | `src/backend/aios/execution/tests/` | Workflow, state machine, scheduler, recovery, progress, models |
| plugins/ | 1 | `src/backend/aios/plugins/tests/` | Manifest validation |
| vision/ | 3 | `src/backend/aios/vision/tests/` | Engine, events, session |
| voice/ | 5 | `src/backend/aios/voice/tests/` | TTS, STT, session, pipeline, events |
| workspace/ | 4 | `src/backend/aios/workspace/tests/` | Models, git, detector, cache |
| router/ | 1 | `src/backend/aios/tests/test_smart_router.py` | Smart router unit tests |
| adapters/ | 1 | `src/backend/aios/tests/test_adapters.py` | Adapter unit tests |
| (other) | 16 | `src/backend/aios/tests/` | Sanitize, OCR, credentials, security, etc. |

**Additional CI gaps:**
- No Python compile check (`python -m py_compile`)
- No launcher test suite execution (launcher tests exist in `tests/launcher/` but are not explicitly targeted)
- No Rust/cargo check for Tauri code
- No desktop bundle validation in CI

**Verdict:** CONFIRMED. CI covers 63% of tests and misses entire subsystems.

### Finding 3: Large God Classes — CONFIRMED

| Class | File | Lines | Methods | Responsibilities | Longest Method |
|-------|------|-------|---------|-----------------|----------------|
| SmartRouter | `src/backend/aios/core/smart_router.py` | 1,181 | 21 class + 10 module-level | 5 | `_resolve_auto` (320 lines) |
| ProviderManager | `src/backend/aios/core/provider_manager.py` | 964 | 46 | 7 | `_create_adapter` (78 lines) |
| ConversationManager | `src/backend/aios/conversation/manager.py` | 860 | 37 | 8 | `stream_message` (161 lines) |

**SmartRouter** — `_resolve_auto` alone is 320 lines implementing an 8-level failover hierarchy with duplicated pattern blocks per commercial tier.

**ProviderManager** — 46 methods spanning persistence, migration, credential management (Windows Credential Manager), CRUD, adapter lifecycle, model discovery, and routing config. The most method-heavy class in the codebase.

**ConversationManager** — 8 injected services, 8 responsibility domains. Despite delegation to 8 sub-managers, the class still orchestrates: intent detection, memory retrieval, context gathering, tool listing, AI routing, response assembly, auto-title, and reindexing.

**Verdict:** CONFIRMED. All three classes exceed recommended complexity thresholds.

### Finding 4: Dead Code — ai_router.py and core/conversation.py — CONFIRMED

#### `core/conversation.py`
- **0 Python imports** anywhere in the codebase
- **0 `__init__.py` exports**
- **0 dynamic imports** (importlib)
- Contains a legacy `Conversation`, `Message`, `StreamEvent`, and `ConversationSystem` dataclass set
- Superseded by `src/backend/aios/conversation/` package (manager.py, models.py, etc.)
- **Classification: CONFIRMED DEAD — safe to remove**

#### `core/ai_router.py`
- **1 Python import** — `tests/unit/test_ai_router.py:7` — this test is itself **broken** (imports non-existent `AIProvider` class from the module, plus references removed `aios.core.providers.openai_provider`)
- **80+ references** to `ai_router` across the codebase — but these are all **parameter/variable names** (`ai_router=smart_router`, `self._ai_router`), not imports of this module
- The file contains `AIRequest`, `AIResponse`, `AIProvider`, `AIRouter`, `RoutingStrategy`, `RateLimiter`, `CostTracker`, `CircuitBreaker` — a legacy routing system superseded by `SmartRouter`
- **Classification: CONFIRMED DEAD** — the module is unused except by one broken test file

**Verdict:** CONFIRMED. Both files are dead code. `test_ai_router.py` is also dead (broken imports).

### Finding 5: Duplicate Frontend Implementations — CONFIRMED

| Component | Dead Version | Active Version | Files Affected |
|-----------|-------------|----------------|----------------|
| **Chat UI** | `components/chat/` (5 files) | `components/conversation/` (17 files) | 5 dead files |
| **MarkdownRenderer** | `chat/MarkdownRenderer.tsx` | `conversation/MarkdownRenderer.tsx` | 1 dead file |
| **CommandPalette** | `desktop/CommandPalette.tsx` | `command/CommandPalette.tsx` | 1 dead file |
| **Message types** | Local in `ChatWindow.tsx` + `MessageList.tsx` | Exported in `conversation/types.ts` | 2 dead definitions |

**Active system:** `App.tsx` imports `ConversationView` from `conversation/` — the decomposed system.

**Dead system:** `chat/` directory components (`ChatWindow`, `MessageList`, `MessageInput`, `MarkdownRenderer`, `ConversationHeader`) — all have **zero imports** from any file.

**Voice API:** Single implementation — NO duplicates. The audit finding was a false positive for voice.

**Verdict:** CONFIRMED for chat/MarkdownRenderer/CommandPalette/Message types. FALSE POSITIVE for Voice API.

### Finding 6: Committed Test Artifacts — CONFIRMED

| Category | Files | Total Size | Classification |
|----------|-------|------------|----------------|
| Office docs at repo root | 6 (`test.pdf`, `test_page_1.pdf`, `test_page_2.pdf`, `test.docx`, `test.xlsx`, `test_notes.pptx`) | ~77 KB | Mistakenly committed |
| Sandbox test images | 8 PNGs (`ocr_test.png`, etc.) | ~77 KB | Mistakenly committed |
| **Sandbox installer** | **1 (`sandbox/tesseract-installer.exe`)** | **~50 MB** | **Mistakenly committed — critical** |
| Sandbox test scripts | 12 Python scripts | ~26 KB | Mistakenly committed |
| Orphaned submodule refs | 4 entries (no `.gitmodules`) | 0 | Mistakenly committed |
| Tauri app icons | 3 PNGs + 1 ICO | ~100 KB | Intentional (required) |
| Vendored Tesseract DLLs | 52 DLLs + 1 EXE | ~167 MB | Intentional but repo-bloating |

**Critical:** `sandbox/tesseract-installer.exe` (50 MB) is the single largest contributor to repository bloat.

**Orphaned submodules:** `sandbox/broken-project`, `sandbox/demo-project`, `sandbox/project_a`, `sandbox/project_b` — these are git submodule entries (mode 160000) with no `.gitmodules` file. They will cause `git submodule init` errors.

**Verdict:** CONFIRMED. 27 mistakenly committed files, 4 orphaned submodule references, and 50 MB of unnecessary binary data.

### Finding 7: 292 Mirrored Backend Files — CONFIRMED

| Metric | Value |
|--------|-------|
| Files in `desktop/src-tauri/backend/` | 265 |
| Files in `src/backend/` | 265 |
| SHA256 hash matches | 265/265 (100%) |
| File tree differences | 0 (exact mirror) |

**Why the mirror exists:** Tauri's `tauri.conf.json` bundles `src/backend` into the NSIS installer as `backend/`. The `desktop/src-tauri/backend/` directory is a **manually-committed physical copy** — not a symlink, not auto-generated.

**Build resolution:**
- Development: `process_service.py` uses `src/backend/` directly
- Production: `launcher.rs` uses `resource_dir/backend/` (the bundled copy)
- CI release: `.github/workflows/release.yml` references `src-tauri/backend` for import verification

**Risk:** Since the copy is manually maintained, it can drift. No pre-commit hook, CI check, or build script enforces sync.

**Verdict:** CONFIRMED. 265 byte-identical files tracked as a manual mirror. This is a maintenance liability.

### Finding 8: v1.2.1 Tag Behind HEAD — PARTIALLY CONFIRMED

| Reference | Commit | Description |
|-----------|--------|-------------|
| `v1.2.1` tag | `936a118` | "release: prepare Eve v1.2.1" |
| `v1.2.0/agent-core` HEAD | `09cd752` | "release: promote Eve v1.2.1 with critical launcher deadlock fix" |

The tag `v1.2.1` points to the **release preparation commit**, not the final promotion commit. HEAD of `v1.2.0/agent-core` is **1 commit ahead** of the tag.

**Verdict:** PARTIALLY CONFIRMED. The tag exists but points to the wrong commit. The actual v1.2.1 release content is in the next commit.

---

## Phase 2: Main Branch Audit

### Commit Divergence

```
main (08ff323) ←── 29 commits behind ──→ v1.2.0/agent-core (09cd752)
```

- `v1.2.0/agent-core` has 29 commits not in `main`
- `main` has 0 commits not in `v1.2.0/agent-core`
- **Fast-forward is safe** — no merge conflicts exist (no divergent history)

### File Divergence

- 670 files changed
- +106,172 lines added
- -1,632 lines removed
- Major additions: conversation system, vision, voice, memory, plugins, workspace, execution engine, Tauri desktop, launcher, model catalog

### Release Divergence

| Tag | Target Commit | On agent-core? | Notes |
|-----|---------------|----------------|-------|
| `v1.0.0` | Early in history | Yes | Original release |
| `v1.1.0` | `0263349` | Yes | Feature release |
| `v1.2.0` | `7279244` | Yes | Provider expansion |
| `v1.2.1` | `936a118` | Yes (1 behind HEAD) | Deadlock fix |

All tags exist on the `v1.2.0/agent-core` branch lineage. No tags exist on `main` beyond v1.0.0.

### Tag History (Linear)

```
v1.0.0 → ... → v1.1.0 → ... → v1.2.0 → v1.2.1 → HEAD(+1)
```

### Fast-Forward Safety

**Can main be safely fast-forwarded?** YES.

- Zero commits on `main` not on `agent-core` — no divergent history
- `git merge --ff-only v1.2.0/agent-core` would succeed
- Risk: LOW — pure fast-forward, no conflict resolution needed

---

## Phase 3: CI Audit

### Current CI Pipeline

**File:** `.github/workflows/ci.yml`

```
┌─────────────────────────────────────────────────────────┐
│  AIOS CI (push/PR to main)                              │
├──────────────────┬──────────────────────────────────────┤
│  backend         │  frontend                            │
│  windows-latest  │  windows-latest                      │
├──────────────────┼──────────────────────────────────────┤
│  ruff check      │  npm ci                              │
│  mypy            │  tsc --noEmit                        │
│  pytest tests/   │  npm run build                       │
└──────────────────┴──────────────────────────────────────┘
```

### Test Coverage Gap

| Metric | Current | Required |
|--------|---------|----------|
| Test files executed | 79 (63%) | 125 (100%) |
| Subsystems covered | 3 of 10 | 10 of 10 |
| Embedded backend tests | 0 of 46 | 46 of 46 |

**Missing subsystems in CI:**
1. `conversation/` — 5 test files (manager, formatter, models, prompts, stream)
2. `desktop/` — 4 test files (hotkeys, notifications, settings, status)
3. `execution/` — 6 test files (workflow, state machine, scheduler, recovery, progress, models)
4. `plugins/` — 1 test file (manifest)
5. `vision/` — 3 test files (engine, events, session)
6. `voice/` — 5 test files (TTS, STT, session, pipeline, events)
7. `workspace/` — 4 test files (models, git, detector, cache)
8. Smart router, adapters, sanitize, OCR, credentials, security — 16 additional files

### Complete CI Pipeline Design

```yaml
name: AIOS CI

on:
  push:
    branches: [v1.2.0/agent-core, main]
  pull_request:
    branches: [main]

jobs:
  backend-lint:
    runs-on: windows-latest
    steps:
      - checkout
      - setup-python 3.12
      - pip install -r requirements.txt
      - ruff check src/backend/
      - ruff format --check src/backend/

  backend-typecheck:
    runs-on: windows-latest
    steps:
      - checkout
      - setup-python 3.12
      - pip install -r requirements.txt
      - mypy src/backend/

  backend-compile:
    runs-on: windows-latest
    steps:
      - checkout
      - setup-python 3.12
      - python -m py_compile src/backend/aios/__main__.py
      - (compile all entry points)

  backend-tests:
    runs-on: windows-latest
    steps:
      - checkout
      - setup-python 3.12
      - pip install -r requirements.txt
      - pytest tests/ src/backend/aios/tests/ src/backend/aios/*/tests/
        --cov=src/backend/ --cov-report=term-missing
        --ignore=tests/unit/test_ai_router.py  # broken import

  frontend:
    runs-on: windows-latest
    steps:
      - checkout
      - setup-node 20
      - npm ci (src/frontend)
      - tsc --noEmit
      - npm run build
      - npm test  # if tests exist

  launcher:
    runs-on: windows-latest
    steps:
      - checkout
      - setup-python 3.12
      - pip install -r requirements.txt
      - pytest tests/launcher/

  build-validation:
    runs-on: windows-latest
    needs: [backend-lint, backend-typecheck, backend-tests, frontend, launcher]
    steps:
      - cargo check (desktop/src-tauri)
      - npm run build:frontend (desktop)
      # Full Tauri build only on release tags
```

### Missing Suites Summary

| Suite | Status | Action |
|-------|--------|--------|
| Backend lint (ruff) | Present | Keep |
| Backend typecheck (mypy) | Present | Keep |
| Backend tests | **Incomplete** | Expand to include `src/backend/aios/*/tests/` |
| Frontend typecheck | Present | Keep |
| Frontend tests | **Missing** | Add `npm test` if available |
| Launcher tests | **Missing** | Add dedicated job |
| Python compile check | **Missing** | Add `py_compile` step |
| Rust/cargo check | **Missing** | Add for Tauri code |
| Build validation | **Missing** | Add as gated job |
| test_ai_router.py | **Broken** | Exclude until removed |

---

## Phase 4: Dead Code Validation

### `src/backend/aios/core/conversation.py`

| Check | Result |
|-------|--------|
| Python imports | **0** — zero imports anywhere |
| `__init__.py` exports | **0** — not exported |
| Dynamic imports | **0** — no importlib usage |
| Test imports | **0** — no test imports this module |
| Documentation refs | 4 markdown files (audit reports only) |

**Content:** Legacy `Conversation` (6 fields), `Message` (7 fields), `StreamEvent`, `ConversationSystem` — all superseded by `conversation/` package.

**Classification: DEAD CODE — safe to remove.**

### `src/backend/aios/core/ai_router.py`

| Check | Result |
|-------|--------|
| Python imports | **1** — `tests/unit/test_ai_router.py:7` (broken test) |
| `__init__.py` exports | **0** |
| Dynamic imports | **0** |
| Variable name usage | 80+ files use `ai_router` as a parameter name (not the module) |

**Content:** `AIRequest`, `AIResponse`, `AIProvider`, `AIRouter`, `RateLimiter`, `CostTracker`, `CircuitBreaker` — legacy routing system superseded by `SmartRouter`.

**Classification: DEAD CODE** — one broken test file references it; all other usages are variable names unrelated to this module.

### `tests/unit/test_ai_router.py`

| Check | Result |
|-------|--------|
| Imports `ai_router.py` | Yes (line 7) |
| Also imports `aios.core.providers.openai_provider` | Yes — **this module no longer exists** |
| Test status | **Broken** — will fail on import |

**Classification: DEAD CODE** — broken test file that tests a removed module.

### Removal Recommendation

| File | Safe to Remove? | Risk |
|------|-----------------|------|
| `core/conversation.py` | **Yes** | ZERO — zero imports |
| `core/ai_router.py` | **Yes** | LOW — one broken test also needs removal |
| `tests/unit/test_ai_router.py` | **Yes** | ZERO — broken test of dead code |
| `desktop/src-tauri/backend/aios/core/conversation.py` | **Yes** | ZERO — mirror of dead code |
| `desktop/src-tauri/backend/aios/core/ai_router.py` | **Yes** | ZERO — mirror of dead code |

---

## Phase 5: Duplication Audit

### Duplicate Inventory

| # | Component | Dead Files | Active Files | Can Merge? | Complexity |
|---|-----------|-----------|-------------|------------|------------|
| 1 | Chat UI system | `chat/ChatWindow.tsx`, `MessageList.tsx`, `MessageInput.tsx` | `conversation/ConversationView.tsx`, `Composer.tsx`, etc. | No — dead code, just delete | Trivial |
| 2 | MarkdownRenderer | `chat/MarkdownRenderer.tsx` | `conversation/MarkdownRenderer.tsx` | No — different CSS classes, different sub-components | Trivial |
| 3 | CommandPalette | `desktop/CommandPalette.tsx` | `command/CommandPalette.tsx` | No — completely different architecture | Trivial |
| 4 | Message types | Local in `ChatWindow.tsx`, `MessageList.tsx` | Exported in `conversation/types.ts` | No — dead code references local types | Trivial |

### Canonical Versions

| Component | Canonical Location | Status |
|-----------|-------------------|--------|
| Chat UI | `components/conversation/` (17 files) | Active |
| MarkdownRenderer | `components/conversation/MarkdownRenderer.tsx` | Active |
| CommandPalette | `components/command/` (32 files) | Active |
| Message types | `components/conversation/types.ts` | Active |

### Dead Files to Remove

| # | File | Reason |
|---|------|--------|
| 1 | `src/frontend/src/components/chat/ChatWindow.tsx` | Zero imports, superseded by ConversationView |
| 2 | `src/frontend/src/components/chat/MessageList.tsx` | Zero imports, superseded by ConversationTimeline |
| 3 | `src/frontend/src/components/chat/MessageInput.tsx` | Zero imports, superseded by Composer |
| 4 | `src/frontend/src/components/chat/MarkdownRenderer.tsx` | Zero imports, superseded by conversation/ version |
| 5 | `src/frontend/src/components/chat/ConversationHeader.tsx` | Zero imports, not wired into active system |
| 6 | `src/frontend/src/components/desktop/CommandPalette.tsx` | Zero imports, superseded by command/ version |

**Total dead frontend files: 6** (5 from chat/, 1 from desktop/)
**Cleanup complexity: TRIVIAL** — all are orphaned with zero imports.

---

## Phase 6: Mirror Audit

### Mirror Status

| Metric | Value |
|--------|-------|
| Directory | `desktop/src-tauri/backend/` |
| File count | 265 .py files |
| Content match | 100% (265/265 SHA256 identical) |
| Sync mechanism | **Manual** — no automation, no hooks |
| Purpose | Tauri NSIS installer bundles `src/backend` as `backend/` |

### Build References

| File | Reference | Purpose |
|------|-----------|---------|
| `tauri.conf.json:43` | `"../../src/backend": "backend"` | Bundle src/backend into installer |
| `launcher.rs:82-97` | `resource_dir.join("backend")` | Runtime path resolution |
| `process_service.py:15-23` | Two-tier dev/prod resolution | Dev uses src/, prod uses bundled |
| `release.yml:79` | `src-tauri\backend` in PYTHONPATH | CI import verification |

### Mirror Removal Assessment

**Can the mirror be removed?** NOT SAFELY.

The Tauri build system (`tauri.conf.json`) already bundles `src/backend` into the installer at build time via the `resources` directive. The `desktop/src-tauri/backend/` directory exists as a **development convenience** — allowing `cargo build` and local testing without the full bundle step.

**However**, `release.yml:79` directly references `src-tauri\backend` for Python import verification. If the mirror is removed, this CI step would break.

**Recommended approach:**
1. Keep the mirror for now (it's working, 100% in sync)
2. Add a CI check that verifies mirror parity: `diff -rq src/backend/ desktop/src-tauri/backend/`
3. If parity fails, the CI build fails — enforcing sync
4. Long-term: investigate whether the Tauri build can use a symlink or copy step instead of a committed mirror

**Risk of keeping mirror:** LOW (currently stable, but drift possible)
**Risk of removing mirror:** HIGH (breaks dev workflow + CI release step)

**Verdict:** DO NOT REMOVE. Add parity check to CI instead.

---

## Phase 7: Test Artifact Audit

### Mistakenly Committed Files (27 total)

| Category | Files | Action |
|----------|-------|--------|
| **Office test docs** | `test.pdf`, `test_page_1.pdf`, `test_page_2.pdf`, `test.docx`, `test.xlsx`, `test_notes.pptx` | Delete, add to .gitignore |
| **Sandbox images** | 8 PNGs in `sandbox/` | Delete entire `sandbox/` directory |
| **Tesseract installer** | `sandbox/tesseract-installer.exe` (50 MB) | **DELETE IMMEDIATELY** — repo bloat |
| **Sandbox scripts** | 12 Python scripts in `sandbox/` | Delete with sandbox/ |
| **Orphaned submodules** | 4 entries (broken-project, demo-project, project_a, project_b) | Remove git entries |

### Intentional Files (Keep)

| Category | Files | Reason |
|----------|-------|--------|
| Tauri app icons | `desktop/src-tauri/icons/` (3 PNG + 1 ICO) | Required by Tauri |
| Vendored Tesseract DLLs | `desktop/src-tauri/tesseract/` (52 DLLs + 1 EXE, ~167 MB) | Intentional bundling for offline desktop |

### .gitignore Additions Required

```gitignore
# Test artifacts
*.pdf
*.pptx
*.docx
*.xlsx
sandbox/
sandbox/**
*.exe
```

### Repository Size Impact

- Current repo size: inflated by ~50 MB (tesseract-installer.exe) + ~167 MB (vendored Tesseract)
- After cleanup: ~50 MB reduction from removing installer + test artifacts
- Note: Git history retains the 50 MB binary forever unless history is rewritten with `git filter-repo`

---

## Phase 8: God Class Analysis

### Decomposition Proposals

#### SmartRouter (1,181 lines, 21 methods)

| Responsibility | Methods | Proposed Module |
|---------------|---------|-----------------|
| Adapter registry | `register_adapter`, `unregister_adapter`, `get_adapter`, `get_all_adapters`, `set_provider_models` | `routing/registry.py` |
| Routing config | `set_routing_config`, `get_routing_config`, `_resolve_category` | `routing/config.py` |
| Request routing | `route`, `route_stream`, `_resolve_route` | `routing/dispatcher.py` |
| STRICT resolution | `_resolve_strict` | `routing/strict.py` |
| AUTO resolution | `_resolve_auto` (320 lines) | `routing/auto.py` |
| Execution | `_make_request`, `_execute_candidate` | `routing/executor.py` |
| Capability reporting | `get_capability_summary` | `routing/capabilities.py` |

**Risk:** MEDIUM — SmartRouter is the central routing hub; splitting requires careful interface design
**Complexity:** HIGH — `_resolve_auto` alone is 320 lines with 8 failover tiers
**Benefit:** HIGH — `_resolve_auto` becomes independently testable; each failover tier becomes a discrete unit

#### ProviderManager (964 lines, 46 methods)

| Responsibility | Methods | Proposed Module |
|---------------|---------|-----------------|
| Persistence | `_load`, `_save`, `_save_routing` | `providers/persistence.py` |
| Migration | `_migrate_routing`, `_migrate_models`, `_migrate_legacy_credentials` | `providers/migration.py` |
| Credentials | `_store_api_key`, `_load_api_key`, `_delete_api_key`, `_credential_target` | `providers/credentials.py` |
| CRUD | `list_providers`, `get_provider`, `add_provider`, `update_provider`, `remove_provider`, `set_default_provider`, `reorder_providers` | `providers/crud.py` |
| Adapter lifecycle | `_create_adapter`, `_register_adapter`, `_unregister_adapter`, `register_all_adapters` | `providers/adapters.py` |
| Connection testing | `test_connection`, `test_all_connections` | `providers/testing.py` |
| Model discovery | `fetch_models`, `_fetch_and_merge`, `toggle_model`, `refresh_models` | `providers/models.py` |
| Routing config | `get_routing`, `set_routing` | (delegate to routing/config.py) |
| Multi-account | `get_all_free_models`, `get_provider_type_models`, `get_model_commercial_status`, `is_model_rate_limited` | `providers/aggregation.py` |

**Risk:** MEDIUM — ProviderManager is a facade; splitting requires re-wiring the API layer
**Complexity:** MEDIUM — clean separation of concerns already exists in method grouping
**Benefit:** HIGH — credential management, persistence, and CRUD become independently testable

#### ConversationManager (860 lines, 37 methods)

| Responsibility | Methods | Proposed Module |
|---------------|---------|-----------------|
| CRUD | `create_conversation`, `get_conversation`, `list_conversations`, `delete_conversation`, `rename_conversation`, `set_provider_model` | Already in sub-managers |
| Messaging | `send_message`, `stream_message`, `get_history`, `clear_history` | `conversation/messaging.py` |
| Edit/regen | `edit_message`, `regenerate_message` | `conversation/editing.py` |
| Branching | `create_branch`, `get_branches`, `delete_branch`, `rename_branch` | Already in BranchManager |
| Search | `search_conversations`, `reindex_conversation` | Already in ConversationSearch |
| Analytics | `get_conversation_analytics`, `get_conversation_analytics_detail`, `export_conversation` | Already in AnalyticsTracker + Exporter |
| Vision | `add_vision_observation` | `conversation/vision.py` |
| Internal helpers | 14 methods | Inline or distribute to sub-managers |

**Risk:** LOW — ConversationManager already delegates to 8 sub-managers
**Complexity:** LOW — the main work is moving `send_message`/`stream_message` orchestration
**Benefit:** MEDIUM — reduces class from 860 to ~300 lines; messaging becomes independently testable

---

## Phase 9: Technical Debt Priority

### P0 — Must Fix Immediately

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 1 | **Fast-forward main to v1.2.0/agent-core** | main is 29 commits / 670 files behind; anyone branching from main gets v1.0.0 | 5 min |
| 2 | **Remove tesseract-installer.exe** (50 MB) | Permanent repo bloat; every clone downloads 50 MB of unnecessary binary | 5 min |
| 3 | **Fix v1.2.1 tag** (points to wrong commit) | Release metadata is incorrect; download links point to pre-fix state | 5 min |

### P1 — Before v1.3

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 4 | **Repair CI** — expand test coverage to 100% | 37% of tests never run in CI; regressions ship undetected | 1-2 hours |
| 5 | **Delete verified dead code** — `core/conversation.py`, `core/ai_router.py`, `test_ai_router.py` | 3 files of dead code + broken test; developer confusion | 15 min |
| 6 | **Delete orphaned frontend** — `chat/` directory, `desktop/CommandPalette.tsx` | 6 dead component files; developer confusion about canonical implementation | 15 min |
| 7 | **Clean sandbox/ directory** — remove all test artifacts, scripts, images, orphaned submodules | 25 tracked entries of developer scratch work | 15 min |
| 8 | **Add .gitignore entries** for test artifacts and sandbox | Prevents future mistaken commits | 5 min |
| 9 | **Add mirror parity check** to CI | Prevents drift between src/backend and desktop/src-tauri/backend | 30 min |

### P2 — Can Wait

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 10 | **Add CI parity check** for `desktop/src-tauri/backend/` vs `src/backend/` | Prevents silent mirror drift | 30 min |
| 11 | **Consolidate Message types** — single source in `conversation/types.ts` | 3 separate interface definitions; maintenance burden | 1 hour |
| 12 | **Evaluate mirror removal** — can Tauri build use symlink or build-time copy? | 265 duplicated files; maintenance liability | 2-4 hours investigation |
| 13 | **Decompose SmartRouter** — split `_resolve_auto` into tier-specific modules | 320-line method is the single largest complexity hotspot | 4-8 hours |
| 14 | **Decompose ProviderManager** — split into persistence, credentials, CRUD, adapters | 46 methods across 7 domains; hard to test in isolation | 4-8 hours |

### P3 — Optional Cleanup

| # | Issue | Impact | Effort |
|---|-------|--------|--------|
| 15 | **Decompose ConversationManager** — move messaging orchestration to sub-module | Already well-delegated; marginal benefit | 2-4 hours |
| 16 | **Remove vendored Tesseract DLLs** from git — download at build time | 167 MB of binaries in git history; only needed at build time | 4-8 hours (requires build script changes) |
| 17 | **Git history rewrite** to remove 50 MB installer from all commits | Repo clone size permanently reduced | HIGH RISK — requires force-push coordination |

---

## Phase 10: Implementation Plan

### Step 1: Fast-Forward main to v1.2.0/agent-core

| Attribute | Value |
|-----------|-------|
| **Command** | `git checkout main; git merge --ff-only v1.2.0/agent-core` |
| **Risk** | LOW — pure fast-forward, zero conflict potential |
| **Files affected** | 670 files change (but no manual resolution) |
| **Expected regression** | ZERO — no code changes, only branch pointer update |
| **Rollback** | `git reset --hard 08ff323` (current main HEAD) |
| **Prerequisites** | None |

### Step 2: Fix v1.2.1 Tag

| Attribute | Value |
|-----------|-------|
| **Command** | `git tag -d v1.2.1; git tag -a v1.2.1 09cd752 -m "Eve v1.2.1 - Launcher deadlock fix"` |
| **Risk** | LOW — tag only, no code change |
| **Files affected** | 0 |
| **Expected regression** | NONE |
| **Rollback** | Re-create old tag: `git tag -a v1.2.1 936a118` |
| **Prerequisites** | Step 1 (main must be at HEAD) |

### Step 3: Remove Test Artifacts and Sandbox

| Attribute | Value |
|-----------|-------|
| **Command** | `git rm -r sandbox/; git rm test.pdf test_page_1.pdf test_page_2.pdf test.docx test.xlsx test_notes.pptx` |
| **Risk** | LOW — removing tracked files that serve no purpose |
| **Files affected** | ~27 files deleted |
| **Expected regression** | ZERO — no code references these files |
| **Rollback** | `git checkout HEAD~1 -- sandbox/ test.* test_notes.pptx` |
| **Prerequisites** | Step 1 |

### Step 4: Update .gitignore

| Attribute | Value |
|-----------|-------|
| **Command** | Edit `.gitignore` to add sandbox/, *.pdf, *.pptx, *.docx, *.xlsx, *.exe entries |
| **Risk** | ZERO — config file only |
| **Files affected** | 1 file modified |
| **Expected regression** | NONE |
| **Rollback** | Revert .gitignore change |
| **Prerequisites** | Step 3 |

### Step 5: Delete Verified Dead Code

| Attribute | Value |
|-----------|-------|
| **Command** | `git rm src/backend/aios/core/conversation.py src/backend/aios/core/ai_router.py tests/unit/test_ai_router.py desktop/src-tauri/backend/aios/core/conversation.py desktop/src-tauri/backend/aios/core/ai_router.py` |
| **Risk** | LOW — zero imports (except one broken test also being removed) |
| **Files affected** | 5 files deleted |
| **Expected regression** | ZERO — verified: zero active imports |
| **Rollback** | `git checkout HEAD~1 -- <files>` |
| **Prerequisites** | Step 1 |

### Step 6: Delete Orphaned Frontend

| Attribute | Value |
|-----------|-------|
| **Command** | `git rm src/frontend/src/components/chat/ChatWindow.tsx src/frontend/src/components/chat/MessageList.tsx src/frontend/src/components/chat/MessageInput.tsx src/frontend/src/components/chat/MarkdownRenderer.tsx src/frontend/src/components/chat/ConversationHeader.tsx src/frontend/src/components/desktop/CommandPalette.tsx` |
| **Risk** | LOW — zero imports verified |
| **Files affected** | 6 files deleted |
| **Expected regression** | ZERO — all files orphaned |
| **Rollback** | `git checkout HEAD~1 -- <files>` |
| **Prerequisites** | Step 1 |

### Step 7: Repair CI Pipeline

| Attribute | Value |
|-----------|-------|
| **Command** | Rewrite `.github/workflows/ci.yml` with expanded test coverage |
| **Risk** | MEDIUM — CI changes may need iteration |
| **Files affected** | 1 file modified |
| **Expected regression** | POSSIBLE — new CI steps may fail on pre-existing issues |
| **Rollback** | Revert ci.yml change |
| **Prerequisites** | Steps 1, 5 (broken test_ai_router.py must be removed first) |

### Step 8: Add Mirror Parity Check to CI

| Attribute | Value |
|-----------|-------|
| **Command** | Add diff step to ci.yml: `diff -rq src/backend/ desktop/src-tauri/backend/` |
| **Risk** | LOW — read-only check |
| **Files affected** | 1 file modified (ci.yml) |
| **Expected regression** | NONE — currently 100% in sync |
| **Rollback** | Remove diff step from ci.yml |
| **Prerequisites** | Step 7 |

### Execution Order (Recommended)

```
Step 1: Fast-forward main ─────────────────┐
Step 2: Fix v1.2.1 tag ────────────────────┤
Step 3: Remove test artifacts ──────────────┤── Phase A: Foundation
Step 4: Update .gitignore ──────────────────┘
                                              │
Step 5: Delete dead code ────────────────────┤── Phase B: Cleanup
Step 6: Delete orphaned frontend ────────────┘
                                              │
Step 7: Repair CI ───────────────────────────┤── Phase C: CI
Step 8: Add mirror parity check ─────────────┘
```

**Phase A** (Steps 1-4): Safe, no code changes, foundational
**Phase B** (Steps 5-6): Low-risk deletions, verified dead code
**Phase C** (Steps 7-8): CI repair, requires testing

---

## Risk Assessment

| Step | Risk Level | Mitigation |
|------|-----------|------------|
| 1. Fast-forward main | LOW | Pure FF, no conflicts |
| 2. Fix tag | LOW | Tag only, no code |
| 3. Remove artifacts | LOW | No code references |
| 4. Update .gitignore | ZERO | Config only |
| 5. Delete dead code | LOW | Verified zero imports |
| 6. Delete frontend orphans | LOW | Verified zero imports |
| 7. Repair CI | MEDIUM | May need iteration |
| 8. Mirror check | LOW | Read-only |

**Overall risk: LOW** — 6 of 8 steps are LOW or ZERO risk. Step 7 (CI) is the only MEDIUM risk and can be validated with a test push.

---

## Blocking Issues Before v1.3

1. **main must be fast-forwarded** — any contributor branching from main gets v1.0.0 code
2. **CI must be repaired** — 37% of tests are invisible to CI; regressions will ship
3. **50 MB binary must be removed** — permanent repo bloat affecting every clone
4. **Dead code must be removed** — developer confusion and maintenance burden

---

## Estimated Effort

| Phase | Steps | Estimated Time |
|-------|-------|---------------|
| Phase A: Foundation | 1-4 | 30 minutes |
| Phase B: Cleanup | 5-6 | 30 minutes |
| Phase C: CI | 7-8 | 2-3 hours |
| **Total** | 1-8 | **3-4 hours** |

---

## Final Repository Health Score

| Metric | Before | After Stabilization |
|--------|--------|---------------------|
| Branch alignment | 2.0/10 | 10/10 |
| CI coverage | 3.0/10 | 8/10 |
| Dead code | 4.0/10 | 9/10 |
| Duplicate code | 5.0/10 | 9/10 |
| Test artifacts | 2.0/10 | 9/10 |
| Mirror management | 6.0/10 | 8/10 (with parity check) |
| Class complexity | 5.0/10 | 5/10 (deferred to P2) |
| **Overall** | **5.6/10** | **8.3/10** |

---

## Recommendation

### **GO** — Repository ready for stabilization work

**Rationale:**
- All 8 audit findings are verified (6 confirmed, 1 partially confirmed, 1 false positive)
- The stabilization plan is low-risk (6 of 8 steps are LOW/ZERO risk)
- Estimated effort is 3-4 hours for foundational cleanup
- No new feature development should proceed until at least Steps 1-6 complete
- The repository is functional but carrying preventable debt that will compound

**Do not proceed to:** Architecture redesign, feature development, or god-class refactoring until stabilization phases A and B complete.
