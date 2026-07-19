# 39. Technical Debt

## Critical

| # | Description | Impact | Recommended Action | Priority |
|---|-------------|--------|-------------------|----------|
| 1 | `conversation/stream.py` line 62: bare `finally:` causes SyntaxError | Blocks all 5 conversation test files (30+ tests) | Fix syntax error | Critical |

## High

| # | Description | Impact | Recommended Action | Priority |
|---|-------------|--------|-------------------|----------|
| 2 | Plugin SDK incomplete — no SDK, loader, validator, verifier, isolator, registry, events, exceptions, models | Blocks third-party plugin ecosystem | Complete Plugin SDK implementation | High |
| 3 | Duplicate CommandPalette components | Code duplication, maintenance burden | Consolidate into single component | High |
| 4 | Duplicate SettingsPanel components | Code duplication, maintenance burden | Consolidate into single component | High |
| 5 | No tests for core modules (Event Bus, DI, Permission Manager, Tool Manager) | Risk of regressions | Add core module tests | High |

## Medium

| # | Description | Impact | Recommended Action | Priority |
|---|-------------|--------|-------------------|----------|
| 6 | No API tests | Risk of API regressions | Add API endpoint tests | Medium |
| 7 | No desktop tests | Risk of desktop regressions | Add desktop module tests | Medium |
| 8 | No frontend tests | Risk of UI regressions | Add frontend component tests | Medium |
| 9 | DIContainer is singleton | Tests cannot run in parallel | Make DIContainer non-singleton or add reset method | Medium |
| 10 | Database is singleton | Tests cannot run in parallel | Make Database non-singleton or add test fixtures | Medium |

## Low

| # | Description | Impact | Recommended Action | Priority |
|---|-------------|--------|-------------------|----------|
| 11 | No integration tests | Risk of integration failures | Add integration tests for critical paths | Low |
| 12 | No end-to-end tests | Risk of system-level failures | Add E2E tests for critical user flows | Low |
| 13 | No frontend tests | Risk of UI regressions | Add component tests | Low |
| 14 | No API tests | Risk of API regressions | Add API endpoint tests | Low |
| 15 | No desktop tests | Risk of desktop regressions | Add desktop module tests | Low |
