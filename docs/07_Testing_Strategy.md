# 07 — Testing Strategy

> **Status:** Approved · v2.1.0  
> **Scope:** Enterprise-grade testing strategy for the Eve OS monorepo  
> **Last Updated:** 2026-07-21  
> **Supersedes:** `docs/18-Testing-Strategy.md`

---

## Table of Contents

1. [Testing Philosophy](#1-testing-philosophy)
2. [Test Pyramid & Distribution](#2-test-pyramid--distribution)
3. [Unit Tests](#3-unit-tests)
4. [Integration Tests](#4-integration-tests)
5. [Component Tests](#5-component-tests)
6. [Accessibility Tests](#6-accessibility-tests)
7. [Performance Tests](#7-performance-tests)
8. [Regression Tests](#8-regression-tests)
9. [Stress Tests](#9-stress-tests)
10. [End-to-End Tests](#10-end-to-end-tests)
11. [Snapshot Tests](#11-snapshot-tests)
12. [Manual Testing](#12-manual-testing)
13. [CI Rules](#13-ci-rules)
14. [Coverage Targets](#14-coverage-targets)
15. [Review Gates](#15-review-gates)
16. [Acceptance Criteria](#16-acceptance-criteria)
17. [Test Naming Conventions](#17-test-naming-conventions)
18. [Folder Structure](#18-folder-structure)
19. [Mocking & Fixtures](#19-mocking--fixtures)
20. [Debugging Workflow](#20-debugging-workflow)
21. [Release Testing](#21-release-testing)
22. [Risk-Based Testing](#22-risk-based-testing)
23. [Tooling & Configuration Reference](#23-tooling--configuration-reference)

---

## 1. Testing Philosophy

### 1.1 Core Tenets

1. **Test behaviour, not implementation.** Tests should verify observable outcomes, not internal method calls. Refactoring-safe tests are the only kind worth writing.

2. **Every test must earn its keep.** A test that is flaky, slow, or duplicated costs more than it provides. Delete or fix such tests immediately.

3. **The pyramid is a guideline, not a straitjacket.** Most code lives in the unit layer, so most tests live there too. But a thin adapter with complex I/O gets an integration test; a critical workflow gets an E2E test. Apply judgement.

4. **CI must be deterministic.** Tests that pass locally must pass in CI. No time-dependent failures, no network-dependent fixtures, no browser-dependent selectors.

5. **Accessibility is a first-class concern.** Every component test must verify ARIA roles, keyboard navigation, and colour contrast. Accessibility bugs are correctness bugs.

6. **Coverage is a lagging indicator.** Chasing 100% line coverage produces brittle tests. Chase meaningful coverage: every public API path, every state transition, every error branch.

### 1.2 Per-Layer Philosophy

| Layer | Philosophy |
|-------|-----------|
| **Python backend** | Fast, isolated, async-native. Tests must not share state. Use `pytest-asyncio` for all async paths. |
| **TypeScript frontend** | User-centric testing via `@testing-library/react`. Never test internal state — test what the user sees and does. |
| **E2E / integration** | Test the seams between layers. Mock at system boundaries, not within modules. |
| **Performance** | Establish baselines in CI. Regressions block merge. No arbitrary thresholds — every number has a rationale. |

---

## 2. Test Pyramid & Distribution

```
         ╱╲
        ╱  ╲           E2E  (3-5%)
       ╱    ╲
      ╱──────╲      Integration  (15-20%)
     ╱        ╲
    ╱──────────╲   Component + Unit  (75-80%)
   ╱            ╲
  ╱──────────────╲
```

| Layer | Target Count (initial) | Target Count (mature) | Run Frequency |
|-------|----------------------|----------------------|---------------|
| Unit (Python) | 65 | 200+ | Every push |
| Unit (TypeScript) | 108 | 300+ | Every push |
| Integration (Python) | 3 | 25+ | Every push |
| Integration (TypeScript) | 0 | 15+ | Every push |
| Component (React) | ~108 | ~300+ | Every push |
| Accessibility | 0 | 50+ | Nightly + per release |
| Performance | 0 | 20+ | Nightly |
| Regression | 0 | 40+ | Per release candidate |
| Stress | 0 | 10+ | Per release candidate |
| E2E | 3 | 20+ | Per PR (smoke) + nightly (full) |
| Snapshot | 0 | 30+ | On change (reviewed) |

---

## 3. Unit Tests

### 3.1 Definition

A unit test verifies a single function, method, or class in isolation. All external dependencies (I/O, databases, network, file system, system clock) are replaced with test doubles.

### 3.2 Python Backend

**Framework:** pytest 8.2+ · pytest-asyncio · unittest.mock

**Discovery:** `tests/test_*.py` and `tests/*/test_*.py` (configured in `pyproject.toml`)

**Rules:**

| Rule | Rationale |
|------|-----------|
| One `assert` per logical outcome | Simplifies debugging — know exactly which assertion failed |
| `asyncio_mode = "auto"` | All `async def test_*` are run in an event loop automatically |
| No network calls | Use `AsyncMock` for HTTP clients, `patch("socket.*")` for sockets |
| No real database | Use `MemorySystem` with in-memory store, mock SQLite connections |
| No real file I/O | Use `tmp_path` fixture for file operations, mock `open()` for reads |
| Mock at the module boundary | Mock `aios.tools.git.run_git`, not `subprocess.run` |
| `@pytest.mark.asyncio` on all async tests | Explicit marker even with auto mode for clarity |
| No shared mutable fixtures | Each test gets fresh instances; use `yield` fixtures with cleanup |
| Test error paths | Every public function that can raise must have a test for each exception path |

**Required patterns:**

```python
# ✅ Correct — test the behaviour
async def test_get_tool_returns_none_for_unknown_tool(tool_manager):
    result = await tool_manager.get_tool("nonexistent")
    assert result is None

# ✅ Correct — mock at module boundary
@patch("aios.tools.git.run_git")
async def test_clone_repo_calls_git(mock_run_git, tool_manager):
    mock_run_git.return_value = (0, "cloned", "")
    result = await tool_manager.execute("git.clone", {"url": "..."})
    assert result.success is True
    mock_run_git.assert_called_once()

# ❌ Wrong — test internal state
async def test_tool_manager_internal_cache(tool_manager):
    await tool_manager._load_tools()  # private method
    assert len(tool_manager._tools) > 0  # private state
```

**Things to unit test in the backend:**
- Event Bus: publish, subscribe, unsubscribe, wildcard patterns, error handling
- AI Router: model selection logic, fallback chains, timeout handling
- Planner: plan construction, dependency resolution, validation
- Tool Manager: tool registration, execution, error wrapping, timeout
- Permission Manager: policy evaluation, role resolution, deny-overrides
- Memory System: CRUD operations, graph queries, vector search, cache eviction
- Context Engine: token budget tracking, window sliding, summarisation triggers
- Plugin lifecycle: state machine transitions (`LOADED→VALIDATED→ENABLED→DISABLED→UNLOADED`)
- Plugin isolator: subprocess management, resource limits, timeout enforcement
- Voice pipeline: STT/TTS model routing, audio format conversion, error recovery
- Vision engine: screen capture encoding, OCR text extraction, window detection
- Execution state machine: all valid + invalid transitions, callback invocation
- Scheduler: dependency ordering, concurrent execution, deadlock detection
- Configuration: YAML parsing, merge strategies, environment variable overrides
- All tool implementations (16 modules): each tool's `execute()` with valid + invalid inputs

### 3.3 TypeScript Frontend

**Framework:** Vitest 4.1.10 · jsdom · @testing-library/react · @testing-library/user-event

**Discovery:** `src/**/*.test.{ts,tsx}` (configured in `vitest.config.ts`)

**Rules:**

| Rule | Rationale |
|------|-----------|
| Use `@testing-library` queries | Prefer `getByRole`, `getByText`, `getByLabelText`. Never use `container.querySelector` |
| Simulate user interactions | Use `userEvent.click()`, `userEvent.type()`, not `fireEvent` |
| No shallow rendering | Render the full component tree (children and all) |
| Mock services, not components | `vi.mock("./services/voice")` is fine; avoid `vi.mock("./Button")` |
| Reset mocks between tests | `afterEach(() => vi.clearAllMocks())` |
| Assert on rendered output | Use `expect(screen.getByRole("button")).toBeInTheDocument()` |
| Test accessibility roles | Assert `getByRole("heading", { level: 1 })`, not `getByText("Title")` |
| Cover all states | empty, loading, error, success, edge case for every component |
| Use `data-testid` sparingly | Only when role/text queries are impossible (e.g., dynamic lists) |

**Required patterns:**

```typescript
// ✅ Correct — test behaviour, not implementation
describe("Composer", () => {
  it("sends message on Enter", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "Hello{Enter}");
    expect(onSend).toHaveBeenCalledWith("Hello");
  });

  it("shows error state when empty message is submitted", async () => {
    const onSend = vi.fn();
    render(<Composer onSend={onSend} />);
    await userEvent.click(screen.getByRole("button", { name: /send/i }));
    expect(onSend).not.toHaveBeenCalled();
    expect(screen.getByText(/message cannot be empty/i)).toBeInTheDocument();
  });
});
```

**Things to unit test in the frontend:**
- **Pure functions:** formatters, validators, selectors (memory core: `store.test.ts`, `graph.test.ts`, `types.test.ts`, `registry.test.ts`, `query.test.ts`, `utils.test.ts`)
- **Hooks:** `useMemoryStore`, `useExecutionState`, `useTheme`
- **Services:** API client methods, voice service, event adapters
- **State machines:** execution session store, command registry, workspace registry

---

## 4. Integration Tests

### 4.1 Definition

Integration tests verify that two or more modules work together correctly. Dependencies beyond the scope of the test are still replaced with test doubles, but the modules under test use real implementations.

### 4.2 Python Backend

**Scope:**

| Test | Modules Involved | What It Verifies |
|------|-----------------|------------------|
| Plugin discovery | PluginLoader + PluginRegistry + PluginValidator | Full discovery→load→validate→register pipeline |
| Vision pipeline | VisionEngine + OCR + WindowDetector + ScreenCapture | End-to-end screen capture→OCR→analysis |
| Voice pipeline | AudioCapture + STT + TTS + PipelineManager | Audio→text→response→audio round trip |
| Conversation flow | ConversationManager + ContextEngine + MemorySystem + AI Router | Full message→context→response→memory write |
| Permission flow | PermissionManager + ToolManager + ExecutionEngine | Policy check→execute→audit log |
| Tool execution | ToolManager + ExecutionEngine + Scheduler | Tool dependency resolution, concurrent execution |
| Plugin lifecycle | PluginManager + PluginIsolator + PluginLifecycle | Full install→enable→run→disable→uninstall |

**Rules:**
- Use real implementations for modules under test, mocks for external I/O
- Each integration test must clean up its own state (database rows, temp files, processes)
- Integration tests are tagged `@pytest.mark.integration` and run in a separate CI job
- A failed integration test must produce enough logging to diagnose without re-running

### 4.3 TypeScript Frontend

**Scope:**

| Test | Modules Involved | What It Verifies |
|------|-----------------|------------------|
| App shell | AppShell + Sidebar + TopBar + StatusBar + Workspace | Full layout renders without error |
| Conversation → Memory | ConversationView + MemoryWorkspace | Message context triggers memory retrieval |
| Execution → Inspector | ExecutionThread + InspectorSession | Selection in thread populates inspector |
| Command → Tool | CommandPalette + API service | Command execution calls correct API endpoint |
| Store → UI | MemoryStore + MemoryGrid | Store updates propagate to UI |

**Rules:**
- Mock only the network layer (`fetch`, WebSocket), not the intermediate service modules
- Render the composite component, not individual pieces
- Integration tests use `data-testid` more freely for multi-component assertions

---

## 5. Component Tests

### 5.1 Definition

Component tests verify a single UI component in isolation, covering all its visual states, interactions, and accessibility requirements. Every component in the catalog (`docs/05_Component_Catalog.md`) must have a corresponding test suite.

### 5.2 Coverage Matrix

Every component must have tests for these states:

| State | What to Verify |
|-------|---------------|
| **Default** | Component renders with required props |
| **Hover** | Visual feedback on hover (where applicable) |
| **Focus** | Visible focus ring, keyboard activation |
| **Active/Pressed** | Transform or colour change |
| **Disabled** | `cursor: not-allowed`, no interaction |
| **Loading** | Spinner/skeleton visible, `aria-busy="true"` |
| **Error** | Error message visible, recovery action present |
| **Empty** | "No data" state with optional CTA |
| **Edge** | Long text, special characters, extreme values |

### 5.3 Existing Component Test Inventory

| Category | Files | Current Coverage |
|----------|-------|-----------------|
| Common (Button, Badge, Card, Icon, Input, Typography) | 6 | Good |
| Conversation (Composer, messages, code blocks, etc.) | 16 | Good |
| Command palette | 13 | Good |
| Execution (cards, threads, progress, permission, etc.) | 17 | Good |
| Activity | 7 | Good |
| Inspector | 11 | Good |
| Layout (AppShell, Sidebar, Panel, SplitPane, etc.) | 14 | Good |
| Memory workspace | 14 | Good |
| **Gaps** | — | **Accessibility, keyboard nav, edge cases** |

### 5.4 Component Test Template

```typescript
describe("ComponentName", () => {
  // 1. Render test
  it("renders with required props", () => { ... });

  // 2. State tests
  it("renders in loading state", () => { ... });
  it("renders in error state", () => { ... });
  it("renders in empty state", () => { ... });

  // 3. Interaction tests
  it("responds to click", async () => { ... });
  it("responds to keyboard Enter", async () => { ... });

  // 4. Accessibility tests
  it("has correct ARIA role", () => { ... });
  it("supports keyboard navigation", async () => { ... });
  it("maintains focus order", async () => { ... });

  // 5. Edge case tests
  it("handles extremely long text", () => { ... });
  it("handles missing optional props", () => { ... });
});
```

---

## 6. Accessibility Tests

### 6.1 Standard

All components must meet **WCAG 2.2 Level AA** as a minimum. Eve OS targets Level AAA where feasible.

### 6.2 Automated Checks

**Tool:** `axe-core` via `@axe-core/react` or `vitest-axe`

Every component test must include an axe audit:

```typescript
import { axe, toHaveNoViolations } from "vitest-axe";
expect.extend(toHaveNoViolations);

it("has no accessibility violations", async () => {
  render(<Button>Submit</Button>);
  const results = await axe(document.body);
  expect(results).toHaveNoViolations();
});
```

**Checklist:**
- [ ] All images have `alt` text (or `role="presentation"` for decorative)
- [ ] All form inputs have associated `<label>` or `aria-label`
- [ ] All interactive elements are keyboard-focusable
- [ ] Focus order follows visual order
- [ ] ARIA roles are correct (see Design System §16.2 for mapping)
- [ ] Colour contrast meets 4.5:1 (text) / 3:1 (large text)
- [ ] Error messages are associated with inputs via `aria-describedby`
- [ ] Dynamic content updates use `aria-live` regions
- [ ] Modal dialogs trap focus and restore on close
- [ ] Touch targets are at least 44×44px

### 6.3 Manual Audits

- Screen reader testing (NVDA on Windows, VoiceOver on macOS) for every release
- Keyboard-only navigation audit for every release
- Colour blindness simulation (use browser DevTools) for every UI change

### 6.4 CI Integration

Accessibility tests run:
- On every PR (automated axe checks in component tests)
- Nightly (full screen-reader regression suite)
- Per release candidate (manual WCAG audit)

---

## 7. Performance Tests

### 7.1 Performance Budget

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Chat response (first token) | < 2s | `time.monotonic()` in E2E tests |
| Tool execution | < 1s | Backend stopwatch, 50th/95th/99th percentiles |
| Memory query | < 500ms | Backend stopwatch |
| UI render (full app) | < 1s | `performance.now()` in Vitest |
| UI interaction response | < 100ms | `userEvent` timing in component tests |
| Concurrent tool executions | 10+ without degradation | Custom stress harness |
| Application startup | < 3s | CI timer, cold start |
| Memory search (10k entries) | < 2s | Benchmark fixture |

### 7.2 Benchmark Suite

Python benchmarks live in `tests/benchmarks/` and use `pytest-benchmark`:

```python
def test_memory_query_latency(benchmark, memory_with_10k_entries):
    result = benchmark(memory_with_10k_entries.query, "test query")
    assert result.status == "completed"
```

Frontend benchmarks use `vitest` with explicit timing assertions:

```typescript
it("renders 500 messages within budget", () => {
  const start = performance.now();
  render(<ConversationView messages={generateMessages(500)} />);
  const elapsed = performance.now() - start;
  expect(elapsed).toBeLessThan(1000);
});
```

### 7.3 Baseline Tracking

- Performance baselines are stored in `docs/performance-baselines.json`
- CI compares current run against baselines
- A regression >10% blocks merge
- Baselines are updated manually after approved performance improvements

---

## 8. Regression Tests

### 8.1 Definition

Regression tests are tests written specifically for bugs that were found in production or during testing. Every bug fix must include a regression test.

### 8.2 Rules

1. **Before fixing a bug, write a test that reproduces it.** The test fails before the fix and passes after.
2. **Tag the test with the issue number:** `@pytest.mark.regression(issue="GH-123")`
3. **Regression tests run in every CI pipeline.** They are not "occasional."
4. **A regression suite that takes >5 minutes to run must be split** into tiers (fast/medium/slow).

### 8.3 Regression Test Categories

| Category | Example |
|----------|---------|
| State machine | "Plugin stuck in LOADING after validation failure" |
| Edge case | "Empty conversation crashes Timeline" |
| Race condition | "Concurrent tool execution loses events" |
| Data integrity | "Memory deduplication drops unrelated entries" |
| UI | "Long tool output overflows message card" |

---

## 9. Stress Tests

### 9.1 Definition

Stress tests push the system beyond normal operating limits to find breaking points.

### 9.2 Scenarios

| Scenario | Load | Expected Behaviour |
|----------|------|-------------------|
| Concurrent conversations | 50 simultaneous conversations | No crash, graceful degradation |
| Rapid tool execution | 100 tools in 1 second | Queueing, no data loss |
| Large message history | 10,000 messages in context | Truncation, acceptable render time |
| Plugin storm | 50 plugins installed simultaneously | Sequential install, no deadlock |
| Memory flood | 100,000 entries in one session | Pagination, search still < 2s |
| UI re-render spam | 1000 state updates per second | Batched renders, no frame drops |

### 9.3 Implementation

Stress tests are implemented as Python scripts in `tests/stress/`:

```python
async def test_concurrent_conversations():
    async def run_conversation(user_id: str):
        conv = await conversation_manager.create(user_id)
        for _ in range(10):
            await conv.send_message("hello")
        return conv.id

    results = await asyncio.gather(*[
        run_conversation(f"user_{i}") for i in range(50)
    ], return_exceptions=True)

    failures = [r for r in results if isinstance(r, Exception)]
    assert len(failures) == 0, f"{len(failures)} conversations failed"
```

### 9.4 Recovery Tests

Stress tests are paired with recovery tests: after the stress load, verify that the system returns to a healthy state (no leaked threads, open file handles, or corrupted state).

---

## 10. End-to-End Tests

### 10.1 Definition

E2E tests exercise the full system stack: UI → API → Backend → External integrations. They use the real application (no mocks) and a dedicated test environment.

### 10.2 Stack

| Layer | Tool | Config |
|-------|------|--------|
| Test runner | Python `pytest` + `playwright` | `tests/e2e/` |
| Browser automation | Playwright (Python) | Installed via `playwright install` |
| API test client | `httpx.AsyncClient` | FastAPI `TestClient` or live server |
| Test database | SQLite `:memory:` or ephemeral file | Cleaned between test suites |
| Test AI model | Mock AI router returning canned responses | `config/test.yaml` |

### 10.3 Scenarios

| Test | Description |
|------|-------------|
| Send message → AI response | User types message, sees AI typing indicator, receives response |
| Execute tool → see result | User types "list files", sees file list rendered |
| Permission request → grant | Tool requests permission, dialog appears, user grants, tool executes |
| Install plugin → use it | User opens plugins, installs, invokes plugin command |
| Search memory | User searches previous conversation, sees results |
| Full workspace workflow | Agent plans, executes multiple tools, presents results |

### 10.4 Existing E2E Tests

| File | Lines | What It Tests |
|------|-------|---------------|
| `tests/e2e/test_agent_scenarios.py` | 977 | Multi-step agent workflows |
| `tests/e2e/test_plugin_lifecycle.py` | — | Full plugin lifecycle |
| `tests/e2e/test_workflows.py` | 928 | System tool workflows |

### 10.5 CI Strategy

| Phase | When | What Runs |
|-------|------|-----------|
| Smoke | Every PR (on label `e2e-smoke`) | 3 critical paths (send message, execute tool, permission grant) |
| Full | Nightly | All E2E scenarios |
| Per release | Release candidate | Full suite + manual verification |

---

## 11. Snapshot Tests

### 11.1 Definition

Snapshot tests capture the rendered output of a component and fail when the output changes unexpectedly. They are a **warning signal**, not a correctness proof.

### 11.2 Policy

- Snapshot tests are permitted only for **pure presentational components** (no branching logic, no side effects).
- Every snapshot must be reviewed by a human before accepting.
- Snapshots must be checked into version control.
- A snapshot diff in a PR must be accompanied by a justification in the PR description.

### 11.3 Implementation

```typescript
it("renders consistently", () => {
  const { container } = render(<Badge variant="success">Active</Badge>);
  expect(container.firstChild).toMatchSnapshot();
});
```

Snapshot files live adjacent to the test file (`__snapshots__/`).

### 11.4 When NOT to Snapshot

- Components with dynamic content (timestamps, random IDs, etc.)
- Components with branching logic (loading, error, empty states — write explicit tests)
- Large trees (snapshots become unreadable; test specific assertions instead)

---

## 12. Manual Testing

### 12.1 When Manual Testing Is Required

| Scenario | Reason |
|----------|--------|
| Visual regression review | Automated tests miss subtle layout shifts, font rendering, animation smoothness |
| Cross-browser verification | Chromium, Firefox, Edge (Eve targets Windows) |
| Screen reader audit | Automated axe checks catch ~30% of accessibility issues |
| Performance feel | 500ms automated vs 500ms perceived are different |
| New feature exploratory | Before writing automated tests, understand how the feature behaves |
| Hard-to-automate scenarios | Multi-step permissions, drag-and-drop, system tray, global hotkeys |

### 12.2 Manual Test Plans

Manual test plans live in `tests/manual/` as markdown files with step-by-step instructions:

```markdown
# Manual Test: Plugin Installation from GitHub

1. Open Eve OS
2. Open Settings → Plugins
3. Click "Install from URL"
4. Enter: https://github.com/example/hello-world-plugin
5. Click Install
6. Verify: Plugin appears in the list
7. Verify: Plugin status is "Enabled"
8. Verify: Plugin command is available in command palette
```

### 12.3 Regression Manual Tests

A "smoke manual test suite" exists for pre-release verification. It covers the 20 most critical user journeys and takes approximately 30 minutes to execute.

---

## 13. CI Rules

### 13.1 Current CI Gap Analysis

| Check | Current CI | Required |
|-------|-----------|----------|
| Python lint (ruff) | ✅ | ✅ — Keep |
| Python type check (mypy) | ✅ | ✅ — Keep |
| Python tests | ✅ | ✅ — Keep |
| Python coverage | ✅ (coveralls) | ✅ — Keep |
| TypeScript type check (tsc --noEmit) | ✅ | ✅ — Keep |
| TypeScript lint (ESLint) | ❌ (no config) | ✅ — Must add |
| TypeScript tests (vitest) | ❌ | ✅ — Must add |
| TypeScript coverage | ❌ | ✅ — Must add |
| Accessibility checks | ❌ | ✅ — Must add |
| Performance benchmarks | ❌ | ✅ — Must add |
| Build check | ✅ | ✅ — Keep |

### 13.2 Required CI Pipeline

```yaml
name: Eve OS CI
on: [push, pull_request]
branches: [main]

jobs:
  backend:
    runs-on: windows-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.12" }
      - run: pip install -r requirements.txt
      - run: pip install -r requirements-dev.txt
      - name: Lint
        run: ruff check src/backend/
      - name: Type check
        run: mypy src/backend/
      - name: Unit + Integration tests
        run: pytest tests/ --cov=src/backend/ --cov-report=term-missing --cov-fail-under=80
      - name: Upload coverage
        uses: codecov/codecov-action@v4
        with: { files: ./coverage.xml, flags: backend }

  frontend:
    runs-on: windows-latest
    defaults: { run: { working-directory: src/frontend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm ci
      - name: Lint
        run: npm run lint
      - name: Type check
        run: npx tsc --noEmit
      - name: Unit + Component tests
        run: npm test -- --coverage --coverage.thresholds.lines=70
      - name: Build
        run: npm run build

  e2e-smoke:
    if: contains(github.event.pull_request.labels.*.name, 'e2e-smoke')
    runs-on: windows-latest
    steps:
      - ...setup...
      - name: Smoke E2E
        run: pytest tests/e2e/ -m smoke -v

  nightly:
    if: github.event_name == 'schedule'
    runs-on: windows-latest
    steps:
      - ...setup...
      - name: Full E2E
        run: pytest tests/e2e/ -v
      - name: Accessibility
        run: npx vitest run --related=src/components --coverage
      - name: Performance benchmarks
        run: pytest tests/benchmarks/ --benchmark-compare --benchmark-autosave
      - name: Stress tests
        run: pytest tests/stress/ --timeout=300 -v
```

### 13.3 Gate Rules

| Gate | Blocking | Non-blocking (alert only) |
|------|----------|---------------------------|
| Lint | Any error | Warnings |
| TypeScript type check | Any error | — |
| Unit tests | Any failure | — |
| Integration tests | Any failure | — |
| Coverage | Below mandatory threshold | Below stretch threshold |
| E2E smoke | Any failure | — |
| Build | Any failure | — |
| Accessibility | Violations in changed files | Violations in unmodified files |
| Performance | Regression > 10% | Regression 5-10% |
| E2E full (nightly) | — | Failure creates GitHub issue |

### 13.4 Flaky Test Management

- A test that fails >1% of the time is **flaky** and must be quarantined
- Quarantined tests go in `pytest.mark.flaky` or `tests/quarantine/` directory
- A GitHub issue is created for each quarantined test
- No flaky test remains quarantined for more than one sprint

---

## 14. Coverage Targets

### 14.1 Current State vs Targets

| Area | Current | Mandatory (M1) | Stretch (M2) |
|------|---------|----------------|--------------|
| Python backend (overall) | Unknown | 80% | 90% |
| Python backend (core) | Unknown | 90% | 95% |
| Python backend (plugins) | Unknown | 75% | 85% |
| Python backend (tools) | Unknown | 75% | 85% |
| TypeScript frontend (overall) | Unknown | 70% | 85% |
| TypeScript frontend (components) | Unknown | 80% | 90% |
| TypeScript frontend (store/selectors) | Unknown | 85% | 95% |
| TypeScript frontend (services) | Unknown | 60% | 75% |

### 14.2 Coverage by Module Priority

| Priority | Module | Mandatory Target |
|----------|--------|-----------------|
| **P0** | Event Bus, AI Router, Permission Manager, Planner | 95% |
| **P0** | Core conversation, execution state machine | 90% |
| **P1** | Tool Manager, Memory System, Context Engine | 85% |
| **P1** | Plugin lifecycle, Plugin isolator | 85% |
| **P2** | Voice pipeline, Vision engine | 75% |
| **P2** | All tool implementations | 70% |
| **P2** | Configuration, Utilities | 60% |

### 14.3 What Coverage Measures

Coverage is measured as **branch coverage**, not line coverage. A line is only counted when all branches through it are executed.

Exceptions to the coverage requirement:
- `__init__.py` files — excluded
- Type stubs (`.pyi`, `.d.ts`) — excluded
- Third-party wrappers without logic — excluded manually
- Error-handling decorators — excluded manually (must be noted in code)

### 14.4 Enforcement

- CI blocks merge if coverage drops below mandatory thresholds
- The `--cov-fail-under` flag enforces the overall backend threshold
- Frontend coverage is enforced via Vitest's `coverage.thresholds` block
- Module-level exceptions must be approved in code review

---

## 15. Review Gates

### 15.1 PR Review Checklist

Every PR must pass these gates before merging:

```
[ ] Code compiles/builds
[ ] Lint passes (ruff/ESLint)
[ ] Type check passes (mypy/tsc)
[ ] All unit + integration tests pass
[ ] Coverage has not decreased
[ ] New code has corresponding tests
[ ] Existing tests were not modified (unless the behaviour changed)
[ ] Accessibility violations in changed files: 0
[ ] No `test.skip` or `it.skip` in committed tests
[ ] No `console.log`, `print()`, or `import pdb` in production code
[ ] No `data-testid` added to production code without justification
[ ] For bug fixes: regression test is included
[ ] For UI changes: screenshot or video in PR description
```

### 15.2 Code Owner Approvals

| Area | Required Approver |
|------|-------------------|
| Backend core (event bus, AI router, permission) | Backend lead |
| Frontend core (AppShell, Sidebar, components) | Frontend lead |
| Memory system | Backend or Memory lead |
| Plugin system | Plugin system maintainer |
| Configuration / Security | Security lead |
| Any coverage exemptions | Tech lead |

### 15.3 Pre-Merge Requirements

- At least 1 approval from a code owner
- All CI checks green
- No unresolved review threads
- PR description includes testing notes
- For E2E-labeled PRs: E2E smoke tests pass

---

## 16. Acceptance Criteria

### 16.1 Feature Acceptance

A feature is considered "tested" when all criteria are met:

```
AC-01: All unit tests pass for new/modified modules
AC-02: Integration tests cover the new workflow end-to-end
AC-03: Component tests (frontend) cover all visual states
AC-04: Accessibility audit shows 0 new violations
AC-05: Performance budget is not exceeded
AC-06: Regression tests exist for any bug fixes
AC-07: Coverage thresholds are maintained or improved
AC-08: Smoke manual test suite passes
AC-09: Documentation is updated (if user-facing)
AC-10: Feature flag is operational (if applicable)
```

### 16.2 Bug Fix Acceptance

```
AC-B01: Regression test reproduces the bug
AC-B02: Fix does not break existing tests
AC-B03: Fix includes error logging for future diagnosis
AC-B04: Root cause is documented in the issue
```

### 16.3 Release Acceptance

```
AC-R01: All CI pipelines pass (backend + frontend + nightly)
AC-R02: Coverage thresholds met for all P0 modules
AC-R03: Full E2E suite passes
AC-R04: Manual smoke test suite passes (signed off)
AC-R05: Accessibility manual audit passes
AC-R06: Performance baseline not regressed beyond threshold
AC-R07: No quarantined flaky tests without active issue
AC-R08: All P0/P1 bugs resolved or deferred with approval
```

---

## 17. Test Naming Conventions

### 17.1 Python

**Files:** `test_<module_name>.py` (e.g., `test_event_bus.py`)

**Classes:** `Test<ModuleName>` (e.g., `class TestEventBus:`)

**Methods:** `test_<action>_<expected_result>` or `test_<action>_when_<condition>`

```
✅ test_publish_delivers_to_subscriber
✅ test_publish_raises_error_when_bus_stopped
✅ test_subscribe_wildcard_matches_multiple_topics
✅ test_register_tool_returns_false_for_duplicate
✅ test_execute_tool_raises_timeout_when_exceeds_limit
❌ test_tool_manager                   # too vague
❌ test_publish                        # what about it?
```

### 17.2 TypeScript

**Files:** `<ComponentName>.test.tsx` (e.g., `Button.test.tsx`)

**Describe block:** `describe("<ComponentName>", () => { ... })`

**Test names:** Present tense, behavioural, full sentences

```
✅ renders with required props
✅ calls onClick when clicked
✅ shows error state when empty message is submitted
✅ focuses the input on mount
✅ prevents default on Enter for new line
✅ adds aria-current="page" for active sidebar item
❌ Button test                           # wrong scope
❌ onClick()                             # unclear expected result
❌ test1                                 # meaningless
```

### 17.3 Test Tags / Markers

| Tag | Scope | Purpose |
|-----|-------|---------|
| `@pytest.mark.asyncio` | Test | Required for all async Python tests |
| `@pytest.mark.integration` | Test | Marks integration tests (separate CI job) |
| `@pytest.mark.e2e` | Test | Marks E2E tests |
| `@pytest.mark.smoke` | Test | Critical path subset of E2E |
| `@pytest.mark.slow` | Test | > 10s execution time |
| `@pytest.mark.regression` | Test | Written for a specific bug fix |
| `@pytest.mark.stress` | Test | Stress/load tests |
| `@pytest.mark.benchmark` | Test | Performance benchmark |
| `@pytest.mark.flaky` | Test | Quarantined flaky tests |
| `it.skip` / `test.skip` | — | Forbidden in committed code |
| `@pytest.mark.skip` | Test | Allowed only with linked issue |

---

## 18. Folder Structure

### 18.1 Python Backend

```
tests/
├── conftest.py                    # Shared fixtures (event_bus, permissions, etc.)
├── fixtures/                      # Shared test data (empty dir — populate per need)
│   ├── plugin_manifests/          # Sample plugin manifests for testing
│   ├── configs/                   # Sample config YAML files
│   └── audio_samples/             # Audio files for voice tests
├── unit/                          # Unit tests
│   ├── test_event_bus.py
│   ├── test_planner.py
│   ├── tools/
│   │   ├── test_git_tools.py
│   │   ├── test_browser_tools.py
│   │   └── ...
│   └── ...
├── integration/                   # Integration tests
│   ├── test_conversation_flow.py
│   ├── test_plugin_discovery.py
│   ├── test_permission_flow.py
│   └── ...
├── e2e/                           # End-to-end tests
│   ├── test_agent_scenarios.py
│   ├── test_plugin_lifecycle.py
│   └── test_workflows.py
├── benchmarks/                    # Performance benchmarks
│   ├── test_memory_query_latency.py
│   └── test_conversation_throughput.py
├── stress/                        # Stress and load tests
│   ├── test_concurrent_conversations.py
│   └── test_rapid_tool_execution.py
├── manual/                        # Manual test plans (.md)
│   ├── plugin-installation.md
│   ├── cross-browser-layout.md
│   └── screen-reader-audit.md
└── quarantine/                    # Flaky tests awaiting fix
    └── test_flaky_example.py
```

### 18.2 TypeScript Frontend

```
src/
└── frontend/
    └── src/
        ├── test/
        │   ├── setup.ts                # Vitest setup (jest-dom matchers, mocks)
        │   ├── test-utils.tsx          # Custom render with providers
        │   └── factories/              # Test data factories
        │       ├── message-factory.ts  # createMockMessage()
        │       ├── execution-factory.ts
        │       └── memory-factory.ts
        ├── __mocks__/                  # Module-level mocks (vitest auto-mock)
        │   ├── services/
        │   │   └── voice.ts
        │   └── api.ts
        ├── components/
        │   ├── Conversation/
        │   │   ├── Composer.test.tsx   # Test co-located with source
        │   │   └── __snapshots__/      # Snapshots (auto-generated)
        │   └── ...
        └── ...
```

### 18.3 Co-location vs Centralisation

| Test Type | Location | Rationale |
|-----------|----------|-----------|
| Component tests | `src/frontend/src/components/*/*.test.tsx` | Co-located with source, easy to find |
| Store/selector unit tests | `src/memory/core/__tests__/*.test.ts` | Co-located with source |
| Service unit tests | `src/services/*.test.ts` | Co-located with source |
| Backend unit tests | `tests/unit/test_*.py` | Centralised (standard Python convention) |
| Backend integration | `tests/integration/test_*.py` | Centralised |
| Internal module tests | `src/backend/aios/*/tests/test_*.py` | Co-located (module-internal testing) |

---

## 19. Mocking & Fixtures

### 19.1 Python Backend

**Existing fixtures** (in `tests/conftest.py`):
- `event_bus` — `EventBus` instance (started and stopped per test)
- `permissions` — `PermissionManager` instance
- `tool_manager` — `ToolManager` with permissions injected
- `memory` — `MemorySystem` instance
- `planner` — `Planner` instance
- `context` — `ContextEngine` instance
- `conversation` — `ConversationSystem` instance
- `capability_registry` — `CapabilityRegistry` instance

**Required new fixtures and factories:**

| Fixture / Factory | Purpose |
|-------------------|---------|
| `mock_ai_router` | Returns canned responses for conversation tests |
| `mock_llm_response` | Returns a specific LLM completion text |
| `mock_screen_capture` | Returns a PIL Image fixture for vision tests |
| `mock_audio_stream` | Returns audio bytes for voice tests |
| `mock_plugin_manifest` | Builds a plugin manifest with given params |
| `memory_with_10k_entries` | Seeds memory with 10k entries for benchmarks |
| `temp_plugin_dir` | Creates a temp directory with plugin files |

**Guidelines:**

```python
# Fixtures — prefer conftest.py or conftest in test directory
@pytest.fixture
def mock_event_bus():
    bus = AsyncMock(spec=EventBus)
    bus.publish = AsyncMock()
    bus.subscribe = AsyncMock()
    return bus

# Factories — use functions, not classes
def create_mock_node(node_id: str, status: str = "completed") -> ExecutionNode:
    return ExecutionNode(id=node_id, status=status, ...)
```

### 19.2 TypeScript Frontend

**Existing setup** (in `src/frontend/src/test/setup.ts`):
- Registers `@testing-library/jest-dom` matchers
- Mocks `scrollIntoView` and `scrollBy`

**Required new factories:**

| Factory | Purpose |
|---------|---------|
| `createMockMessage(overrides)` | Builds a message object with defaults |
| `createMockExecution(overrides)` | Builds an execution session with defaults |
| `createMockMemoryEntry(overrides)` | Builds a memory entry with defaults |
| `createMockPlugin(overrides)` | Builds a plugin descriptor |
| `createMockCommand(overrides)` | Builds a command palette entry |

**Guidelines:**

```typescript
// Factories in src/frontend/src/test/factories/
export function createMockMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: crypto.randomUUID(),
    role: "user",
    content: "Test message",
    timestamp: Date.now(),
    tool_calls: [],
    ...overrides,
  };
}

// Mock services — vi.mock at top of test file
vi.mock("@/services/api", () => ({
  api: {
    sendMessage: vi.fn().mockResolvedValue({ id: "mock-1" }),
    getTools: vi.fn().mockResolvedValue([]),
  },
}));
```

### 19.3 What to Mock vs What Not to Mock

| Mock | Don't Mock |
|------|-----------|
| HTTP/gRPC/WebSocket connections | Business logic |
| File system operations | Data transformations |
| System clock (`time`, `Date.now()`) | Pure functions |
| External APIs (OpenAI, GitHub, etc.) | Internal module-to-module calls (prefer real) |
| Subprocess/Sandbox execution | Synchronous utility functions |
| Audio playback/capture | String operations |

---

## 20. Debugging Workflow

### 20.1 Local Test Debugging

**Python:**

```bash
# Run a single test with verbose output
pytest tests/unit/test_event_bus.py::TestEventBus::test_publish -vvs

# Run with pdb on failure
pytest tests/unit/test_event_bus.py --pdb

# Run with full traceback
pytest tests/unit/test_event_bus.py --tb=long

# Run with live logging
pytest tests/unit/test_event_bus.py -o log_cli=true --log-cli-level=DEBUG
```

**TypeScript:**

```bash
# Run a single test file
npx vitest run src/components/Conversation/Composer.test.tsx

# Watch mode with UI
npx vitest --ui

# Run tests matching a pattern
npx vitest run -t "sends message"
```

### 20.2 CI Test Failure Diagnosis

1. Check CI logs for exact error message and stack trace
2. For flaky tests: check if the test passed in the last 10 runs (GitHub Actions "Re-run jobs")
3. Reproduce locally with the same command from CI logs
4. If environment-dependent: use `act` (local GitHub Actions runner) or CI's debug mode
5. For E2E failures: check Playwright trace/screenshot artifacts
6. For performance regressions: compare against last known good baseline

### 20.3 Debugging Infrastructure

| Technique | When to Use |
|-----------|------------|
| `print()` / `console.log()` | Quick local exploration (remove before commit) |
| `pdb.set_trace()` | Complex control flow debugging |
| `--pdb` on pytest | Test failure postmortem |
| `import logging; logging.getLogger()` | Production issue reproduction |
| Playwright trace viewer | E2E test failures |
| React DevTools | Component state inspection during manual testing |
| Browser DevTools "Rendering" tab | Layout/paint debugging |

---

## 21. Release Testing

### 21.1 Release Candidate Checklist

```
[ ] All CI checks pass (see §15.1)
[ ] Full E2E suite passes on RC branch
[ ] Manual smoke test suite signed off (QA lead)
[ ] Accessibility manual audit signed off
[ ] Performance baseline verified (no regression > 10%)
[ ] All P0/P1 bugs resolved or deferred
[ ] No flaky tests quarantined > 1 sprint
[ ] Stress tests pass
[ ] Regression tests pass
[ ] Security scan passes (SAST + dependency audit)
[ ] Coverage thresholds met
[ ] Version bump consistency verified
[ ] Changelog updated
```

### 21.2 Release Test Stages

```
Stage 1 — Automated (CI)
  ├── All unit + integration tests
  ├── Coverage check
  ├── Lint + type check
  ├── Build check
  └── E2E smoke tests

Stage 2 — Nightly (scheduled)
  ├── Full E2E
  ├── Performance benchmarks
  ├── Stress tests
  ├── Security tests
  └── Accessibility automated suite

Stage 3 — RC (manual)
  ├── Manual smoke test suite
  ├── Screen reader audit
  ├── Cross-browser audit
  ├── Visual regression review
  └── Performance feel assessment

Stage 4 — Release
  ├── Sign-off from QA lead
  ├── Sign-off from tech lead
  ├── Sign-off from product owner
  └── Release notes published
```

### 21.3 Post-Release

- Monitor error rates for 48 hours post-release
- Collect performance metrics and compare against baselines
- If critical bug found: patch release within 24 hours
- If non-critical: add to next sprint backlog
- Update performance baselines after release stabilises

---

## 22. Risk-Based Testing

### 22.1 Risk Matrix

| Risk Level | Impact | Testing Requirement |
|------------|--------|---------------------|
| **Critical** | Data loss, security breach, system crash | Full coverage: unit + integration + E2E + stress + security audit |
| **High** | Feature unusable, major degradation | Unit + integration + E2E |
| **Medium** | Feature partially broken, minor degradation | Unit + integration |
| **Low** | Cosmetic, edge cases | Unit tests |

### 22.2 Risk Classification by Module

| Module | Risk Level | Rationale |
|--------|-----------|-----------|
| Permission Manager | **Critical** | Security boundary |
| Memory System | **Critical** | Data integrity |
| Event Bus | **Critical** | Foundation for all communication |
| Execution Engine | **Critical** | Runs arbitrary code on system |
| AI Router | **High** | Core UX path |
| Plugin System | **High** | Third-party code execution |
| Conversation System | **High** | Core UX path |
| Tool Manager | **High** | All tool execution |
| Voice Pipeline | **Medium** | Non-critical feature |
| Vision Engine | **Medium** | Non-critical feature |
| Configuration | **Medium** | Global settings |
| UI Components | **Low-Medium** | Visual only (most are P2) |

---

## 23. Tooling & Configuration Reference

### 23.1 Python Test Stack

| Tool | Version | Purpose | Config Location |
|------|---------|---------|-----------------|
| pytest | 8.2+ | Test runner | `pyproject.toml` |
| pytest-asyncio | latest | Async test support | `pyproject.toml` |
| pytest-cov | 5.0+ | Coverage reporting | CLI flags |
| pytest-benchmark | latest | Performance benchmarks | `tests/benchmarks/` |
| pytest-timeout | latest | Test timeout enforcement | CLI flags |
| httpx | latest | Async HTTP client for API tests | `requirements.txt` |
| ruff | 0.4+ | Linter | CLI flags |
| mypy | 1.10+ | Type checker | CLI flags |
| playwright (Python) | latest | Browser automation | `tests/e2e/` |

### 23.2 TypeScript Test Stack

| Tool | Version | Purpose | Config Location |
|------|---------|---------|-----------------|
| Vitest | 4.1.10 | Test runner | `vitest.config.ts` |
| @testing-library/react | 16.3.2 | Component testing | `setup.ts` |
| @testing-library/user-event | 14.6.1 | User interaction simulation | `setup.ts` |
| @testing-library/jest-dom | 6.9.1 | DOM matchers | `setup.ts` |
| jsdom | 29.1.1 | DOM environment | `vitest.config.ts` |
| vitest-axe | latest | Automated a11y checks | Test files |
| @vitejs/plugin-react | latest | JSX transform | `vitest.config.ts` |

### 23.3 CI Configuration

**File:** `.github/workflows/ci.yml`

Must be updated to include:
- Frontend test execution (`npm test -- --coverage`)
- Coverage thresholds in Vitest config
- E2E smoke job (triggered by label)
- Nightly schedule for full E2E + stress + benchmarks

### 23.4 Configuration Snippets

**pyproject.toml (pytest section):**

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
markers = [
    "integration: marks tests as integration tests",
    "e2e: marks tests as end-to-end tests",
    "smoke: critical path smoke tests",
    "slow: marks tests as slow (>10s)",
    "regression(issue): regression test for a specific issue",
    "stress: stress/load tests",
    "benchmark: performance benchmark tests",
    "flaky: quarantined flaky tests",
]
```

**vitest.config.ts (coverage block):**

```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html", "lcov"],
      include: ["src/**/*.{ts,tsx}"],
      exclude: [
        "src/**/*.test.{ts,tsx}",
        "src/test/**",
        "src/**/*.d.ts",
      ],
      thresholds: {
        lines: 70,
        branches: 60,
        functions: 70,
        statements: 70,
      },
    },
  },
});
```
