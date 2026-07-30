# 38. Testing Review

## Test Coverage (Current)

| Module | Tests | Status | Notes |
|--------|-------|--------|-------|
| Core (EventBus, DI, Permission, ToolManager, Capability, Config, Planner, Memory, LLM) | ~160 | ✅ | Solid coverage |
| Context Engine | 85 | ✅ | Polling, events, project detection |
| Conversation Manager | 363 | ✅ | Models, manager, service, sessions, branching, search, analytics, export, streaming |
| Browser Automation | 214 | ✅ | Engine, tools, models, legacy |
| Developer Tools (Sprint 20) | 152 | ✅ | All 7 services + tool registration + integration |
| API Routes | ~30 | ✅ | Chat, tools, context, memory, websocket endpoints |
| E2E / Integration | 0 | ❌ | 2 tests exist but INTERNALERROR on this platform |
| **Adapters (WindowsAdapter, BaseAdapter)** | **0** | ❌ | No tests |
| **Voice module** | **0** | ❌ | No tests |
| **Vision module** | **0** | ❌ | No tests |
| **Tool implementations (all categories)** | **0** | ❌ | No tests for individual tool handlers |
| **core/windows/ subsystem** | **0** | ❌ | No tests |
| **chat_engine** | **0** | ❌ | No tests |
| **Plugin system** | **0** | ❌ | No tests |
| **Frontend** | **0** | ❌ | No tests |

**Total passing:** 1,094 tests, 0 failures
**Warnings:** 226 (down from 20,886 after `datetime.utcnow()` migration)

## Test Organization

Tests are organized per module in `tests/` subdirectory. Each module has its own test file(s).

## Mocking Strategy

No mocking framework is used. Tests use temporary directories and real OS calls where possible.

## Known Issues

- `tests/e2e/test_agent_scenarios.py` triggers a pytest path resolution INTERNALERROR on this platform (`ValueError: 'path' is not in the subpath of 'path'`)
- 2 e2e test items fail with INTERNALERROR (pytest infrastructure bug, not test logic)

## Missing Coverage (Priority Order)

1. **Adapter module tests** — `BaseAdapter`, `WindowsAdapter` (both `adapters/` and `core/windows/`)
2. **Voice module tests** — STT, TTS, pipeline, session
3. **Vision module tests** — engine, session, pipeline, models
4. **Tool implementation tests** — per-handler unit tests for all ~800 tools (currently only ToolManager is tested)
5. **ChatEngine tests** — core AI orchestration
6. **Plugin system tests** — plugin manager, SDK
7. **E2E / Integration tests** — end-to-end user flows
8. **Frontend tests** — React/TypeScript component tests
