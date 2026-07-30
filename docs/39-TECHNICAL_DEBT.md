# 39. Technical Debt

**Last Updated:** 2026-07-21

## Resolved Items

| # | Description | Resolution |
|---|-------------|------------|
| 1 | `conversation/stream.py` line 62: bare `finally:` causes SyntaxError | No longer blocking — 363 conversation tests pass |
| 5 | No tests for core modules (Event Bus, DI, Permission Manager, Tool Manager) | ✅ ~160 tests now exist |
| 6 | No API tests | ✅ ~30 API tests exist |
| 13 | No API tests (duplicate) | ✅ Resolved |
| 14 | No desktop tests | ✅ DevTools has 152 tests |
| — | `datetime.utcnow()` deprecation — 20K+ warnings | ✅ Migrated to `datetime.now(timezone.utc)` across 28 files |
| — | Missing `await` on `create_node` in ContextEngine | ✅ Fixed |
| — | ContextEngine not wired with WindowsAdapter or MemoryStore | ✅ Fixed |
| — | ToolManager not wired with CapabilityRegistry or EventBus | ✅ Fixed |
| — | 7 tool categories (~765 tools) not registered | ✅ Fixed — all 9 categories now registered |
| — | `os.sysinfo()` on Windows | ✅ Fixed — uses `platform.version()` |

## Remaining Debt

### High Priority

| # | Description | Impact | Recommended Action |
|---|-------------|--------|-------------------|
| 1 | Plugin SDK incomplete — no SDK, loader, validator, verifier, isolator, registry, events, exceptions, models | Blocks third-party plugin ecosystem | Complete Plugin SDK implementation |
| 2 | No tests for adapters, voice, vision modules | Risk of regressions | Add coverage for all untested modules |
| 3 | No tests for ~800 tool implementations | Tool handler bugs undetected | Add per-category tool handler tests |
| 4 | Synchronous I/O in async tool handlers blocks event loop | Performance degradation in production | Wrap blocking calls in `asyncio.to_thread()` or use async libraries |

### Medium Priority

| # | Description | Impact | Recommended Action |
|---|-------------|--------|-------------------|
| 5 | DIContainer is singleton | Tests cannot run in parallel | Add `reset()` method or use factory per test |
| 6 | Massive tool files (50K–62K lines each) | Maintenance burden | Split into subpackages per category |
| 7 | `adapters/windows_adapter.py` dead code (superseded by `core/windows/`) | Confusion, maintenance burden | Remove or deprecate |
| 8 | `tool()` decorator uses unsafe `create_task` in sync context | Latent crash risk | Keep current guard or remove decorator |
| 9 | `pytest` INTERNALERROR in `tests/e2e/` | Blocks E2E test execution | Fix test path configuration |

### Low Priority

| # | Description | Impact | Recommended Action |
|---|-------------|--------|-------------------|
| 10 | No frontend tests | Risk of UI regressions | Add React component tests |
| 11 | No integration or E2E tests | Risk of system-level failures | Add end-to-end user flow tests |
| 12 | Database singleton | Tests cannot run in parallel | Add test-specific fixtures |
| 13 | File tool path traversal protection missing | Security risk mitigated by permission level | Add input sanitization |
| 14 | CORS is permissive (allow all origins) | Security risk for production | Restrict in production config |
