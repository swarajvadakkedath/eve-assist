# System Integration & Production Readiness Audit Report

**Date:** 2026-07-21
**Scope:** Full codebase audit covering architecture, DI, Event Bus, API, Tools, Capabilities, Memory, Windows Adapter, duplicate code, startup sequence, tests, documentation, and remaining debt.

---

## Executive Summary

**Test Suite:** 1095 ✅ passing, 0 actual failures, 2 INTERNALERROR (pytest path bug in `tests/e2e/`)
**Modules:** 15 completed modules across 2 phases
**Tools Registered in app.py:** ~35 (builtin + system + browser + vision)
**Tools NOT Registered (existing but unwired):** ~765+ (content, developer, devtools, git, network, office, productivity)
**Critical Bugs Found:** 3 (1 blocks memory storage, 1 is a latent runtime crash, 1 is incorrect platform API usage)
**Docs Out of Sync:** 5 docs need updating

---

## 1. Verified Critical Bugs

### Bug 1 — Missing `await` on async call (HIGH)
**File:** `src/backend/aios/core/context/engine.py:246`
```python
self._memory_store.create_node(node_input)  # Missing await!
```
`create_node` is `async def` in the `MemoryStore` protocol. The returned coroutine is never awaited, so **all context observations silently fail to persist**. This means the memory system never receives context observations, breaking any downstream feature that depends on context history.

### Bug 2 — `os.sysinfo()` on Windows (LOW)
**File:** `src/backend/aios/adapters/windows_adapter.py:89`
```python
os_version = os.sysinfo() if hasattr(os, "sysinfo") else ""
```
`os.sysinfo()` does not exist on any Python platform. The `hasattr` guard returns `False`, so it silently returns `""`. Harmless but indicates the code was never tested on Windows or the error handling path was never verified. Should use `platform.version()`.

### Bug 3 — `asyncio.create_task()` in synchronous decorator (MEDIUM)
**File:** `src/backend/aios/core/tool_manager.py:163`
```python
def tool(self, ...) -> Callable:
    def decorator(handler: Callable) -> Callable:
        ...
        asyncio.create_task(self.register_tool(contract, handler))  # ⚠️
        return handler
    return decorator
```
If the `@tool_manager.tool()` decorator is ever used at module level (outside an async context), this will raise `RuntimeError: no running event loop`. Currently no tool file uses this decorator (all use `register_*()` functions called from the async `lifespan()`), so this is **latent** — but a ticking bomb for future code.

---

## 2. Startup & DI Wiring Audit

### app.py Startup Sequence

| Step | Action | Issues |
|------|--------|--------|
| 1 | Load `AiosSettings` | OK |
| 2 | Setup logging | OK |
| 3 | Create `EventBus(max_retries, retry_delay)` | OK |
| 4 | `EventBus.start()` | OK |
| 5 | Create `PermissionManager(event_bus, config)` | OK |
| 6 | `permissions.configure(default_level, sensitive_actions, session_timeout)` | OK |
| 7 | Create `ToolManager(permissions)` | OK — but no CapabilityRegistry or EventBus passed |
| 8 | Create `CapabilityRegistry()` | Orphaned — not wired into ToolManager |
| 9 | Create `AIRouter()` | OK |
| 10 | Create `MemorySystem(event_bus)` | OK |
| 11 | Create `Planner()` | OK |
| 12 | Create `ContextEngine(poll_interval)` | ⚠️ No `windows_adapter` or `memory_store` passed — will silently do nothing |
| 13–82 | ConversationManager, ConversationService, StatusService, SettingsStore, AppShell, HotkeyManager, NotificationService, WindowManager, StartupManager, ExecutionEngine, WorkspaceManager, PluginManager, Voice/Vision systems | See notes below |
| 89 | `register_builtin_tools(tool_manager)` | 6 basic tools |
| 90 | `register_system_tools(tool_manager, event_bus)` | System tools |
| 170 | `register_vision_tools(tool_manager, vision_engine, vision_session)` | Vision tools |
| 173 | `register_browser_tools(tool_manager, browser_engine, vision_engine, event_bus)` | Browser tools |

### Missing Registrations

**7 tool categories NOT registered in app.py:**
- `register_content_tools` — exists in `tools/content_tools.py`
- `register_developer_tools` — exists in `tools/developer_tools.py`
- `register_devtools_tools` — exists in `tools/devtools_tools.py`
- `register_git_tools` — exists in `tools/git_tools.py`
- `register_network_tools` — exists in `tools/network_tools.py`
- `register_office_tools` — exists in `tools/office_tools.py`
- `register_productivity_tools` — exists in `tools/productivity_tools.py`

**Impact:** Only ~35 tools are available at runtime out of ~800+ defined. Users cannot use devtools, git, network, office, productivity, content, or developer tools.

### ContextEngine Missing Dependencies
`ContextEngine` is created with only `poll_interval` — no `windows_adapter` and no `memory_store`. This means:
- `_poll()` always returns `None` (line 151-152) because `self._windows is None`
- Even if polling worked, `_store_context_observation()` would silently pass on the `except` block
- **Context awareness is completely non-functional at startup**

---

## 3. Event Bus Audit

### Published Events (all modules)

| Event Prefix | Source Module | In Event Catalog (34)? |
|---|---|---|
| `system:startup`, `system:shutdown` | app.py | ✅ Yes |
| `error:occurred` | Event Bus | ✅ Yes |
| `conversation:*` | ConversationManager | ✅ Yes |
| `execution:*` | ExecutionEngine | ✅ Yes |
| `workspace:*` | WorkspaceManager | ✅ Yes |
| `desktop:status` | StatusService | ✅ Yes |
| `tool:*` (started/completed/failed/timeout) | ToolManager | ✅ Yes |
| `context:*` (changed, project_changed, file_changed, activity_changed, application_changed, engine_started, engine_stopped, poll_error) | ContextEngine | ❌ Missing |
| `debug:*` (eval/exec/inspect/session_cleared) | DevTools DebugConsole | ❌ Missing |
| `health:updated` | DevTools HealthDashboard | ❌ Missing |
| `module:inspected` | DevTools ModuleInspector | ❌ Missing |
| `hot_reload:*` (completed/failed/watch_added/removed/polling_started/stopped) | DevTools HotReload | ❌ Missing |
| `diagnostics:completed` | DevTools Diagnostics | ❌ Missing |
| `perf:*` (monitoring_started/stopped, metrics) | DevTools PerformanceMonitor | ❌ Missing |
| `log:*` (entry/cleared/level_changed) | DevTools LogViewer | ❌ Missing |
| `clipboard:*` (read/changed) | WindowsAdapter | ❌ Missing |
| `file:*` (read/changed) | WindowsAdapter | ❌ Missing |
| `process:*` (started/stopped) | WindowsAdapter | ❌ Missing |
| `active_window:changed` | WindowsAdapter | ❌ Missing |

### Event Bus Issues
- `ValueError` is raised in `_dispatch` handler if a callback raises an exception, breaking the dispatch loop for future events
- Max retries/retry delay are configured but not actually used in the dispatch logic
- Wildcard subscriptions work but are inefficient (O(n) scan on every publish)

---

## 4. API Route Audit

| Route | Method | File | Status |
|-------|--------|------|--------|
| `/api/v1/chat` | POST | `api/chat.py` | ✅ |
| `/api/v1/chat/stream` | GET (SSE) | `api/chat.py` | ✅ |
| `/api/v1/chat/history` | GET | `api/chat.py` | ✅ |
| `/api/v1/chat/clear` | POST | `api/chat.py` | ✅ |
| `/api/v1/tools` | GET | `api/tools.py` | ✅ |
| `/api/v1/tools/{tool_id}` | GET | `api/tools.py` | ✅ |
| `/api/v1/tools/execute` | POST | `api/tools.py` | ✅ |
| `/api/v1/tools/search` | GET | `api/tools.py` | ✅ |
| `/api/v1/capabilities` | GET | `api/capabilities.py` | ✅ |
| `/api/v1/settings` | GET/PUT | `api/settings.py` | ✅ |
| `/api/v1/plugins` | GET | `api/plugins.py` | ✅ |
| `/api/v1/permissions` | POST/GET | `api/permissions.py` | ✅ |
| `/api/v1/memory` | GET/POST | `api/memory.py` | ✅ |
| `/api/v1/system/health` | GET | `api/app.py` | ✅ |
| `/api/v1/system/status` | GET | `api/app.py` | ✅ |
| Desktop routes | Various | `api/desktop.py` | ✅ |
| Execution routes | Various | `api/execution.py` | ✅ |
| Workspace routes | Various | `api/workspace.py` | ✅ |
| Voice routes | Various | `api/voice.py` | ✅ |
| Vision routes | Various | `api/vision.py` | ✅ |

**No duplicate routes found.** All routes follow the `/api/v1` prefix convention. Two routes (desktop, voice, vision) are mounted without the prefix — minor inconsistency.

---

## 5. Windows Adapter Audit

### Two Implementations Exist

| Aspect | `adapters/windows_adapter.py` | `core/windows/adapter.py` |
|--------|-------------------------------|---------------------------|
| Lines | 120 | 309 |
| Pattern | Direct calls to psutil/pyautogui/pygetwindow | Facade with sub-services + permission gating + events |
| Permission checks | ❌ None | ✅ Full permission gating |
| Event publishing | ❌ None | ✅ Full event publishing |
| DI registration | ❌ None | ✅ `register_in_container()` |
| Used by app.py? | ❌ No | ⚠️ ContextEngine imports it but app.py doesn't pass it |
| Status | **Old/deprecated** | **Current — but not wired** |

### Direct Win32/psutil calls outside WindowsAdapter

| Location | Calls | Verdict |
|----------|-------|---------|
| `devtools/performance_monitor.py:81` | `psutil.cpu_percent()`, `psutil.virtual_memory()` | ⚠️ Should go through WindowsAdapter |

---

## 6. Memory System Compliance

### Direct `_store.graph` access outside MemoryStore

| Location | Pattern | Verdict |
|----------|---------|---------|
| `core/context/engine.py:246` | `self._memory_store.create_node()` | ✅ Uses protocol — but missing `await` |
| All tool files | Use `ToolResult` pattern | ✅ No memory graph access |

**No unauthorized memory graph manipulation found.** All memory access goes through the `MemoryStore` protocol or stays within the memory system.

### Duplicate Model Definitions
- `aios/models/memory.py` and `aios/core/models/memory.py` — both define identical `MemoryStore`, `NodeInput`, `EdgeInput`
- Only `core/models/memory.py` is imported by actual code (`core/context/models.py`)
- **Dead code:** `aios/models/memory.py` and `aios/models/message.py`

---

## 7. Tool Registration Audit

### Tool Registration Pattern

Every tool file follows the same pattern:
```python
def register_<category>_tools(tm: ToolManager, ...) -> None:
    tools = [ToolContract(...), ...]
    handlers = [_handler1, _handler2, ...]
    for contract, handler in zip(tools, handlers):
        asyncio.create_task(tm.register_tool(contract, handler))
```

**Issue:** `asyncio.create_task()` in every registration function means tools are registered asynchronously. If called from a context where you need synchronous guarantees (e.g., before serving requests), tools may not be fully registered yet.

### Tool Count Per Category

| Category | File | Tools | Registered? |
|----------|------|-------|-------------|
| builtin | `builtin.py` | 6 | ✅ |
| system | `system_tools.py` | ~15 | ✅ |
| browser | `browser_tools.py` | ~28 | ✅ |
| vision | `vision/tools.py` | ~5 | ✅ |
| devtools | `devtools_tools.py` | 32 | ❌ |
| developer | `developer_tools.py` | ~200 | ❌ |
| git | `git_tools.py` | ~200 | ❌ |
| content | `content_tools.py` | ~50 | ❌ |
| network | `network_tools.py` | ~80 | ❌ |
| office | `office_tools.py` | ~80 | ❌ |
| productivity | `productivity_tools.py` | ~100 | ❌ |

---

## 8. Test Coverage Audit

### Test Suite Results
**1095 passed, 0 failed, 2 INTERNALERROR** (pytest path resolution bug, not test failures)

| Module | Tests | Status |
|--------|-------|--------|
| Core (EventBus, DI, Permission, ToolManager, Capability, Config, Planner, Memory, LLM) | ~160 | ✅ Tests exist |
| Context Engine | 85 | ✅ Tests exist |
| Conversation Manager | 363 | ✅ Tests exist |
| Browser Automation | 214 | ✅ Tests exist |
| Developer Tools | 152 | ✅ Tests exist |
| API Routes | ~30 | ✅ Tests exist |
| WebSocket | ~10 | ✅ Tests exist |
| **Adapters (WindowsAdapter, BaseAdapter)** | **0** | ❌ No tests |
| **Voice module** | **0** | ❌ No tests |
| **Vision module** | **0** | ❌ No tests |
| **Tool implementations (all categories)** | **0** | ❌ No tests |
| **core/windows/** subsystem | **0** | ❌ No tests |
| **chat_engine** | **0** | ❌ No tests |
| **Plugin system** | **0** | ❌ No tests |
| **Frontend** | **0** | ❌ No tests |
| **E2E/integration** | **0** | ❌ 2 tests exist but crash with pytest bug |

### Warnings
20,886 warnings across the test suite, almost all `DeprecationWarning: datetime.utcnow()` — should migrate to `datetime.now(timezone.utc)`.

---

## 9. Documentation Sync Status

| Doc | Current? | Issues |
|-----|----------|--------|
| 02-System-Architecture.md | ⚠️ Partial | Architecture is accurate but doesn't document DevTools, Voice, Vision subsystems |
| 09_ADR_Log.md | ✅ | OK |
| 11_Project_Status.md | ⚠️ Partial | Shows module completion but references "Sprint 9/10" as planned when they're done |
| 30-IMPLEMENTATION_PLAN.md | ⚠️ Partial | Sprint plan reflects older state |
| 33-DEPENDENCY_ANALYSIS.md | ⚠️ Minimal | Only has a high-level diagram, no actual dependency analysis |
| 34-EVENT_CATALOG.md | ❌ **Stale** | Missing 25+ events from ContextEngine, DevTools, WindowsAdapter |
| 35-PUBLIC_API_REVIEW.md | ⚠️ Partial | Only covers interfaces from 3 modules, missing DevTools, Browser, Voice, Vision, Context |
| 36-PERFORMANCE_REVIEW.md | ⚠️ Outdated | References phase 2 state, doesn't account for voice/vision/devtools overhead |
| 37-SECURITY_REVIEW.md | ⚠️ Good | Still relevant, recommendations still apply |
| 38-TESTING_REVIEW.md | ❌ **Stale** | Claims "0 core tests" and "0 API tests" — now has 1095 tests |
| 39-TECHNICAL_DEBT.md | ❌ **Stale** | Lists items already resolved (#5, #6, #14 all now have tests), missing new debt items |
| 40-RISK_ASSESSMENT.md | ⚠️ Still valid | Phase risks still accurate |
| 41-ROADMAP_VALIDATION.md | ✅ | Still accurate |

---

## 10. Remaining Technical Debt

### New Debt Items (not in doc 39)

| # | Description | Severity | Action |
|---|-------------|----------|--------|
| 1 | Missing `await` on `engine.py:246` — context observations lost | **Critical** | Add `await` |
| 2 | 7 tool categories (~765 tools) not registered in app.py | **High** | Wire into `lifespan()` |
| 3 | `ToolManager` created without `CapabilityRegistry` or `EventBus` | **High** | Wire both in |
| 4 | `ContextEngine` created without `windows_adapter` or `memory_store` | **High** | Wire both in |
| 5 | `asyncio.create_task` in synchronous `tool()` decorator | **Medium** | Use `asyncio.ensure_future` or require async registration |
| 6 | Duplicate `models/memory.py` (dead code) | **Low** | Remove `aios/models/` directory |
| 7 | `adapters/windows_adapter.py` deprecated — unused | **Low** | Remove or consolidate |
| 8 | `datetime.utcnow()` deprecation — 15K+ warnings | **Medium** | Migrate to timezone-aware `now()` |
| 9 | No tests for adapters, voice, vision, tool implementations | **High** | Add coverage |
| 10 | Massive tool files (50K–62K lines) should be modularized | **Medium** | Split into subpackages |
| 11 | Synchronous I/O in async tool handlers blocks event loop | **Medium** | Wrap in `asyncio.to_thread` or use async libs |
| 12 | `pytest` e2e test path resolution bug | **Low** | Fix test file path or conftest |
| 13 | Event catalog (34) missing 25+ events | **Medium** | Sync with actual code |
| 14 | Testing review (38), Tech debt (39) docs badly outdated | **Medium** | Rewrite to match reality |

---

## 11. Recommendations for Release Candidate

### Must-Fix Before RC

1. **Add `await` to `engine.py:246`** — 1-line fix, critical
2. **Wire `ToolManager` with `CapabilityRegistry` and `EventBus`** in `app.py:69`
3. **Wire `ContextEngine` with `windows_adapter` and `memory_store`** in `app.py:74`
4. **Register remaining 7 tool categories** in `app.py` lifespan
5. **Fix `datetime.utcnow()`** across codebase — simple sed/find-replace

### Should-Fix Before RC

6. Add tests for adapter, voice, vision modules
7. Sync all documentation to match current code state
8. Clean up duplicate `models/memory.py` and deprecated `adapters/windows_adapter.py`
9. Fix `os.sysinfo()` in `windows_adapter.py:89`
10. Add path traversal protection to file tools

### Nice-to-Have

11. Reorganize massive tool files into subpackages
12. Wrap synchronous I/O in tool handlers with `asyncio.to_thread()`
13. Fix the `tool()` decorator to use `asyncio.ensure_future` or document as async-only
14. Add integration/E2E tests

---

## Appendix: Summary Metrics

| Metric | Value |
|--------|-------|
| Total Python files | ~80+ |
| Total lines of code | ~280K |
| Passing tests | 1095 |
| Test failures | 0 (2 INTERNALERROR in pytest itself) |
| Modules completed | 15 |
| Tool categories | 9 (but only 4 registered at startup) |
| Tools defined | ~800+ |
| Tools registered at startup | ~35 |
| Event types defined | ~50+ |
| Event types in catalog | ~30 |
| API routes | ~20+ |
| Critical bugs | 1 (await missing) |
| High-priority issues | 5 |
| Documentation gaps | 5 stale docs |
