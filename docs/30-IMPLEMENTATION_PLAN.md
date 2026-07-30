# Implementation Plan

**Document ID:** 30-IMPLEMENTATION_PLAN  
**Status:** Approved  
**Version:** 1.0.0  
**Last Updated:** 2026-07-18

---

## 1. Purpose

This document is the engineering execution plan for building AIOS v1.0. It defines every sprint, including objectives, scope, dependencies, deliverables, technical tasks, tests, acceptance criteria, risks, and estimated effort.

## 2. Sprint Overview

| Sprint | Module | Effort | Dependencies | Status |
|--------|--------|--------|-------------|--------|
| 1 | Foundation | 3 days | None | ✅ |
| 2 | Configuration | 1 day | Sprint 1 | ✅ |
| 3 | Logger | 1 day | Sprint 2 | ✅ |
| 4 | Event Bus | 3 days | Sprint 3 | ✅ |
| 5 | Dependency Injection | 1 day | Sprint 4 | ✅ |
| 6 | AI Router | 3 days | Sprint 5 | ✅ |
| 7 | Permission Manager | 2 days | Sprint 5 | ✅ |
| 8 | Tool Manager | 3 days | Sprint 7 | ✅ |
| 9 | Capability Registry | 2 days | Sprint 8 | ✅ |
| 10 | Memory System | 3 days | Sprint 9 | ✅ |
| 11 | Planner | 3 days | Sprint 9, 10 | ✅ |
| 12 | Context Engine | 2 days | Sprint 13 | ✅ |
| 13 | Windows Adapter | 3 days | Sprint 8 | ✅ |
| 14 | Conversation Manager | 2 days | Sprint 14 | ✅ |
| 15 | Browser Automation | 2 days | Sprint 13 | ✅ |
| 16 | Chat UI | 4 days | Sprints 5, 6, 14 | 🔜 |
| 17 | Voice | 3 days | Sprint 15 | ✅ |
| 18 | Vision System | 3 days | Sprint 13 | ✅ |
| 19 | Plugin System | 4 days | Sprint 9 | ✅ |
| 20 | Developer Tools | 2 days | Sprint 19 | ✅ |
| I | System Integration | 1 day | All | ✅ |
| 21 | Eve Launcher (Sprint 1) | 2 days | All | ✅ |
| I | Sprint 1.5 — Launcher Refactor | 2 days | Sprint 21 | ✅ |
| 3 | 2 — Tauri Desktop Shell | 2 days | Sprint 1.5 | ✅ |
| 22 | AIOS v1.0 | 3 days | All | 🔜 |

**Total estimated effort:** 54 days

---

## 3. Sprint Details

### Sprint 1: Foundation

**Objective:** Set up the project structure, tooling, and CI pipeline

**Scope:** Repository initialization, folder structure, package managers, build tools, linting, CI configuration

**Dependencies:** None

**Deliverables:**
- Initialize Git repository
- Create folder structure per 05-Folder-Structure.md
- Set up Python virtual environment and requirements.txt
- Set up Node.js project with package.json
- Set up Tauri configuration
- Configure ESLint, Prettier, Ruff, mypy
- Set up GitHub Actions CI
- Create README.md with setup instructions

**Technical Tasks:**
1. Initialize Git repo with `.gitignore`
2. Create directory structure:
   - `src/backend/aios/{core,adapters,tools,vision,plugins,models,db,api,utils}`
   - `src/frontend/src/{components,hooks,stores,services,types,utils,styles}`
   - `tests/{unit,integration,e2e,fixtures}`
   - `scripts/`, `config/`, `resources/`
3. Create `pyproject.toml` for Python project
4. Create `requirements.txt` with core dependencies:
   - fastapi, uvicorn, pydantic, pydantic-settings
   - structlog, aiosqlite
   - pytest, pytest-asyncio, pytest-cov
   - httpx, openai, anthropic
   - psutil, pyautogui, pillow, pytesseract
   - playwright
5. Create `package.json` for frontend:
   - react, react-dom, typescript
   - tailwindcss, vite
   - @tauri-apps/api
6. Create `.github/workflows/ci.yml` with:
   - Python tests (pytest, coverage)
   - TypeScript lint (ESLint)
   - Python lint (ruff, mypy)
7. Create `README.md`

**Tests:**
- CI pipeline runs successfully
- `python -m venv venv && pip install -r requirements.txt` succeeds
- `npm install` succeeds

**Acceptance Criteria:**
- `git clone && npm install && pip install` works
- CI passes on PR
- Folder structure matches architecture docs

**Risks:**
- None — standard project setup

**Estimated Effort:** 3 days

---

### Sprint 2: Configuration

**Objective:** Implement centralized configuration management

**Scope:** Pydantic settings, YAML config files, environment variables

**Dependencies:** Sprint 1

**Deliverables:**
- `src/backend/aios/config/__init__.py`
- `src/backend/aios/config/settings.py` — Pydantic BaseSettings
- `src/backend/aios/config/defaults.py` — Default values
- `config/default.yaml` — Default configuration
- `config/development.yaml` — Dev overrides
- `config/schema.yaml` — Configuration schema

**Technical Tasks:**
1. Implement `AiosSettings` class with Pydantic:
   - `AI_PROVIDER`, `AI_API_KEY`, `AI_MODEL`
   - `DB_PATH`, `LOG_LEVEL`, `LOG_FORMAT`
   - `PERMISSION_DEFAULT_LEVEL`, `SESSION_TIMEOUT`
   - `UI_THEME`, `LANGUAGE`
   - `PLUGINS_ENABLED`, `PLUGIN_PATH`
   - `WINDOWS_ADAPTER_TIMEOUT`
   - `EVENT_BUS_MAX_RETRIES`, `EVENT_BUS_RETRY_DELAY`
2. Implement config file loading (YAML + env override)
3. Implement config validation with `pydantic`
4. Create `get_settings()` singleton factory
5. Write unit tests

**Tests:**
- `test_default_settings` — Default values are correct
- `test_env_override` — Environment variables override defaults
- `test_config_file_loading` — YAML file loading
- `test_config_validation` — Invalid config raises error
- `test_settings_singleton` — Same instance returned

**Acceptance Criteria:**
- Settings load from defaults
- Environment variables override
- YAML files override
- Validation rejects invalid config
- Single instance throughout app

**Risks:**
- None

**Estimated Effort:** 1 day

---

### Sprint 3: Logger

**Objective:** Implement structured logging

**Scope:** structlog configuration, log levels, output formatting

**Dependencies:** Sprint 2

**Deliverables:**
- `src/backend/aios/utils/logger.py`
- Log level configuration
- Structured JSON output
- Console and file handlers

**Technical Tasks:**
1. Implement `setup_logging()` function
2. Configure structlog with:
   - JSON renderer for production
   - Console renderer for development
   - Timestamp, level, module name
   - Correlation ID support
3. Implement log level management
4. Implement file rotation
5. Create `get_logger(name)` factory
6. Write unit tests

**Tests:**
- `test_logger_creation` — Logger instance created
- `test_log_levels` — DEBUG, INFO, WARNING, ERROR
- `test_structured_output` — JSON format
- `test_correlation_id` — Correlation ID in logs
- `test_file_logging` — File rotation works

**Acceptance Criteria:**
- Logs are structured JSON
- Log levels configurable
- File rotation works
- Correlation IDs propagate

**Risks:**
- None

**Estimated Effort:** 1 day

---

### Sprint 4: Event Bus

**Objective:** Implement the core communication backbone

**Scope:** Publish/subscribe, event lifecycle, retry, dead letters, persistence

**Dependencies:** Sprint 3

**Deliverables:**
- `src/backend/aios/core/event_bus.py`
- `src/backend/aios/models/events.py`
- Event catalog implementation
- Retry with exponential backoff
- Dead letter queue
- Event persistence to SQLite

**Technical Tasks:**
1. Implement `Event` dataclass:
   - `id` (UUID), `type` (str), `source` (str)
   - `timestamp` (datetime), `payload` (dict)
   - `correlation_id` (str), `retry_count` (int)
   - `priority` (int: 0=normal, 1=high, 2=critical)
2. Implement `EventBus` class:
   - `publish(event_type, payload, priority) -> str`
   - `subscribe(event_type, handler) -> UUID`
   - `unsubscribe(subscription_id) -> bool`
   - `get_history(event_type, limit) -> list[Event]`
3. Implement `Subscription` management
4. Implement event delivery with asyncio
5. Implement retry strategy:
   - Max 3 retries
   - Exponential backoff (1s, 2s, 4s)
   - Dead letter after max retries
6. Implement event persistence to SQLite
7. Implement priority queue
8. Write unit and integration tests

**Tests:**
- `test_publish_subscribe` — Handler receives events
- `test_unsubscribe` — Handler stops receiving
- `test_retry_mechanism` — Retry on failure
- `test_dead_letter` — Max retries exceeded
- `test_priority_queue` — High priority delivered first
- `test_event_persistence` — Events stored in DB
- `test_correlation_id` — IDs propagate
- `test_concurrent_subscribers` — Handlers run in parallel

**Acceptance Criteria:**
- Events delivered to subscribers
- Retry with backoff works
- Dead letters logged
- Events persisted to SQLite
- Priority queue works
- All existing events documented

**Risks:**
- None

**Estimated Effort:** 3 days

---

### Sprint 5: Dependency Injection ✅

**Objective:** Implement DI container for module wiring

**Scope:** DI container, module lifecycle, service registration

**Dependencies:** Sprint 4

**Deliverables:**
- `src/backend/aios/core/di_container.py` ✅
- Module registration and resolution ✅
- Singleton and factory scopes ✅
- Lifecycle management ✅

**Technical Tasks:**
1. Implement `DIContainer` class:
   - `register(interface, implementation, scope="singleton")` ✅
   - `resolve(interface) -> implementation` ✅
   - `create_scope() -> DIContainer` ✅
2. Implement module registration at startup ✅
3. Implement lifecycle hooks:
   - `on_init()`, `on_start()`, `on_stop()` ✅
4. Write unit tests ✅

**Tests:**
- `test_register_resolve` — Module resolved correctly ✅
- `test_singleton_scope` — Same instance returned ✅
- `test_factory_scope` — New instance each time ✅
- `test_lifecycle_hooks` — init/start/stop called ✅
- `test_module_dependencies` — Nested resolution ✅

**Acceptance Criteria:**
- Modules resolved from container ✅
- Singleton scope works ✅
- Lifecycle hooks called ✅
- No circular dependencies ✅

**Risks:**
- None

**Estimated Effort:** 1 day

**Completed:** 2026-07-21 — 143 lines, 11 unit tests, 0 lint errors

---

### Sprint 6: AI Router

**Objective:** Implement AI provider abstraction and routing

**Scope:** Provider abstraction, routing strategies, failover, rate limiting

**Dependencies:** Sprint 5

**Deliverables:**
- `src/backend/aios/core/ai_router.py`
- `src/backend/aios/core/ai_provider.py` — Abstract base
- OpenAI provider implementation
- Anthropic provider implementation
- Ollama (local) provider implementation
- Routing strategies (cost, latency, performance)
- Failover manager
- Rate limiter
- Cost tracker

**Technical Tasks:**
1. Implement `AIProvider` abstract base:
   - `chat()`, `chat_stream()`, `embed()`
   - `health_check()`, `model`, `capabilities`
2. Implement `OpenAIProvider`:
   - GPT-4, GPT-3.5 support
   - Streaming support
   - Tool calling support
   - Vision support
3. Implement `AnthropicProvider`:
   - Claude 3 support
   - Streaming support
   - Tool calling support
4. Implement `OllamaProvider`:
   - Local model support
   - Basic chat support
5. Implement `AIRouter`:
   - `route()`, `route_stream()`
   - `register_provider()`, `health_check()`
6. Implement routing strategies:
   - Cost strategy — Use cheapest capable model
   - Latency strategy — Use fastest provider
   - Performance strategy — Use most capable model
   - Fallback strategy — Try providers in order
7. Implement `RateLimiter`:
   - Per-provider rate limits
   - Token-based rate limiting
   - Queue management
8. Implement `CostTracker`:
   - Track tokens per request
   - Track cost per provider
   - Persist to SQLite
9. Write unit tests

**Tests:**
- `test_provider_chat` — Chat response received
- `test_provider_stream` — Stream yields tokens
- `test_provider_health` — Health check returns bool
- `test_router_routing` — Request routed to correct provider
- `test_router_failover` — Fallback on failure
- `test_rate_limiter` — Rate limiting enforced
- `test_cost_tracker` — Costs tracked correctly
- `test_provider_registration` — Dynamic provider registration

**Acceptance Criteria:**
- Multiple AI providers supported
- Automatic failover works
- Rate limiting enforced
- Costs tracked per request
- Providers replaceable via config

**Risks:**
- API keys required for cloud providers
- Rate limit configuration may need tuning

**Estimated Effort:** 3 days

**Completed:** 2026-07-21 — 3 provider implementations, RateLimiter, CostTracker, CircuitBreaker, 4 routing strategies, 40 unit tests, 0 lint errors

---

### Sprint 7: Permission Manager ✅

**Objective:** Implement permission-gated execution

**Scope:** Permission levels, confirmation flows, session management, history, audit, event bus integration, DI container registration, config integration, REST API

**Dependencies:** Sprint 5

**Deliverables:**
- `src/backend/aios/core/permission_manager.py` ✅
- `src/backend/aios/api/permissions.py` ✅ — REST endpoints
- 4 permission levels ✅
- Session permissions with monotonic timing expiry ✅
- Permission history / audit log (in-memory) ✅
- Audit filtering (by tool_id, decision, limit) ✅
- REST API endpoints ✅
- Event Bus integration (`permission:requested/granted/denied/expired`) ✅
- DI Container registration (`register_in_container` static method) ✅
- Config integration (sensitive actions, default level, session timeout) ✅
- Default-deny policy for SENSITIVE level ✅
- `permission_sensitive_actions` config setting ✅

**Technical Tasks:**
1. Implement `PermissionLevel` enum ✅:
   - `READ` (0) — Auto-approve
   - `SAFE` (1) — Auto-approve
   - `WORKSPACE` (2) — Session confirm
   - `SENSITIVE` (3) — Always confirm
2. Implement `PermissionRequest` dataclass ✅
3. Implement `PermissionManager` ✅:
   - `check_permission(tool_id, level) -> PermissionResult` ✅ — with `_apply_default_level` enforcement
   - `request_permission(request) -> PermissionResult` ✅
   - `grant_permission(request_id)` ✅
   - `deny_permission(request_id, reason)` ✅
   - `get_pending_requests() -> list[PermissionRequest]` ✅
   - `get_audit_history(tool_id, decision, limit) -> list[AuditEntry]` ✅
   - `configure(default_level, sensitive_actions, session_timeout)` ✅
   - `register_in_container(container, event_bus, config)` ✅
4. Implement session permission cache ✅:
   - Workspace permissions expire after configurable timeout (default 5 min)
   - Uses `time.monotonic()` for timing
5. Implement permission audit persistence (in-memory) ✅:
   - Every request, grant, deny, expiry creates an `AuditEntry`
   - Filterable by tool_id, decision, limit
6. Implement Event Bus integration ✅:
   - `permission:requested` — on `request_permission()`
   - `permission:granted` — on `grant_permission()`
   - `permission:denied` — on `deny_permission()`
   - `permission:expired` — on session expiry in `_check_session_valid()`
   - Zero overhead when no Event Bus provided
7. Implement DI Container registration ✅:
   - `PermissionManager.register_in_container(container, event_bus, config)` static method
8. Implement config integration ✅:
   - `permission_default_level` from `AiosSettings` — floor for all levels
   - `permission_sensitive_actions` from `AiosSettings` — auto-escalate to SENSITIVE
   - `session_timeout_seconds` from `AiosSettings` — session duration
9. Implement API endpoints ✅:
   - `GET /api/v1/permissions/pending` — list pending requests
   - `POST /api/v1/permissions/grant` — approve a request
   - `POST /api/v1/permissions/deny` — reject a request
   - `GET /api/v1/permissions/audit` — query audit history
10. Wire PermissionManager in app.py ✅ — constructed with event_bus and config settings
11. Write unit tests (38 tests, expanded from 6) ✅

**Tests:** (38 tests, expanded from 6)
- `test_read_auto_approve` — Read level auto-approved ✅
- `test_safe_auto_approve` — Safe level auto-approved ✅
- `test_sensitive_requires_approval` — Sensitive always requires confirm ✅
- `test_grant_permission` — Permission granted ✅
- `test_deny_permission` — Permission denied ✅
- `test_pending_requests` — Pending list returned ✅
- `test_workspace_session_grant` — Session permission works ✅
- `test_session_expiry` — Workspace permission expires ✅
- `test_session_uses_monotonic_clock` — Uses `time.monotonic()` ✅
- `test_audit_tracks_requested` — Audit entry on request ✅
- `test_audit_tracks_granted` — Audit entry on grant ✅
- `test_audit_tracks_denied` — Audit entry on deny ✅
- `test_audit_filter_by_tool` — Filter audit by tool_id ✅
- `test_audit_filter_by_decision` — Filter audit by decision ✅
- `test_audit_limit` — Audit result limit ✅
- `test_audit_entry_structure` — AuditEntry field types ✅
- `test_check_sensitive_default_deny` — Default-deny for sensitive ✅
- `test_request_sensitive_default_deny` — Default-deny on request ✅
- `test_grant_nonexistent_raises` — ValueError on bad grant ✅
- `test_deny_nonexistent_raises` — ValueError on bad deny ✅
- `test_request_publishes_event` — `permission:requested` event ✅
- `test_grant_publishes_event` — `permission:granted` event ✅
- `test_deny_publishes_event` — `permission:denied` event ✅
- `test_expiry_publishes_event` — `permission:expired` event ✅
- `test_configure_sensitive_actions` — Sensitive actions enforced ✅
- `test_configure_session_timeout` — Timeout configurable ✅
- `test_configure_default_level` — Default level floor enforced ✅
- `test_register_in_container` — DI registration ✅
- `test_factory_produces_permission_manager` — Factory creates PM ✅
- `test_factory_with_event_bus` — Factory passes event bus ✅
- `test_auto_approved_not_sensitive` — Auto-approve vs session ✅
- `test_session_approved_not_auto` — Session vs auto-approve ✅
- `test_no_event_bus_no_crash` — Graceful without event bus ✅
- `test_load_config_no_config` — Graceful without config ✅
- `test_load_config_with_config` — Config values applied ✅
- `test_audit_entry_dataclass` — AuditEntry dataclass ✅
- `test_configure_sensitive_actions_list` — Multiple sensitive actions ✅
- `test_session_approval_expired_clears_entry` — Expired entry removed ✅

**Acceptance Criteria:**
- 4 permission levels work correctly ✅
- Auto-approve for read/safe ✅
- Session confirm for workspace ✅
- Always confirm for sensitive ✅
- Permission audit persisted ✅
- API endpoints functional ✅
- Event Bus integration publishes lifecycle events ✅
- DI Container registration works ✅
- Config integration (sensitive actions, default level, session timeout) ✅
- Default-deny policy enforced ✅
- 38 tests passing, 0 lint errors ✅

**Risks:**
- None

**Estimated Effort:** 2 days

**Completed:** 2026-07-21 — ~294 lines core, 132 lines API, 38 unit tests, 0 lint errors

---

### Sprint 8: Tool Manager ✅ ✅

**Objective:** Implement tool registration and execution

**Scope:** Tool contracts, registration, validation, execution, error handling, Event Bus integration, DI Container registration

**Dependencies:** Sprint 7

**Deliverables:**
- `src/backend/aios/core/tool_manager.py` ✅
- `src/backend/aios/core/tool_manager.py:ToolManagerError` — base exception ✅
- `src/backend/aios/core/tool_manager.py:ValidationError` — typed exception ✅
- `src/backend/aios/core/tool_manager.py:ToolTimeoutError` — typed exception ✅
- `src/backend/aios/core/tool_manager.py:ToolExecutionError` — typed exception ✅
- JSON Schema parameter validation ✅
- Timeout enforcement via `asyncio.wait_for()` ✅
- Event Bus integration (`tool:started`, `tool:completed`, `tool:failed`, `tool:timeout`) ✅
- DI Container registration (`register_in_container` static method) ✅
- Backward-compatible with existing tool implementations (productivity_tools, plugin tools) ✅

**Technical Tasks:**
1. Implement `ToolContract` dataclass ✅
2. Implement `ToolResult` dataclass ✅
3. Implement `ToolManager`:
   - `register_tool(contract, handler)` ✅
   - `execute(tool_id, params) -> ToolResult` ✅ — with validation, timeout, event publishing
   - `get_tool(tool_id) -> ToolContract` ✅
   - `list_tools(category) -> list[ToolContract]` ✅
   - `search_tools(query) -> list[ToolContract]` ✅
   - `unregister_tool(tool_id)` ✅
4. Implement JSON Schema parameter validation ✅
   - Validates `required` fields, `properties` type constraints
   - Returns `ValidationError` with descriptive message
   - Does not execute invalid requests
5. Implement timeout enforcement ✅
   - `asyncio.wait_for()` around handler execution
   - Returns `ToolTimeoutError` with duration measurement
   - Publishes `tool:timeout` event
6. Implement Event Bus integration ✅
   - Optional `event_bus` parameter in constructor
   - Events: `tool:started`, `tool:completed`, `tool:failed`, `tool:timeout`
   - Zero overhead when no Event Bus provided
7. Implement DI Container registration ✅
   - `ToolManager.register_in_container(container, ...)` static method
   - Optional `permission_manager`, `capability_registry`, `event_bus` overrides
8. Implement typed exceptions ✅
   - `ToolManagerError` — base
   - `ValidationError(code="VALIDATION_ERROR")`
   - `ToolTimeoutError(code="TOOL_TIMEOUT")`
   - `ToolExecutionError(code="TOOL_EXECUTION_ERROR")`
   - Raw exceptions are wrapped; no exception type leaks beyond `ToolManagerError`
9. Write unit tests (27 tests, expanded from 10) ✅

**Tests:**
- `test_register_tool` — Tool registered successfully ✅
- `test_execute_tool` — Tool executed successfully ✅
- `test_tool_not_found` — Error for unknown tool ✅
- `test_list_tools` — Tools listed by category ✅
- `test_search_tools` — Tools searchable by query ✅
- `test_tool_decorator` — Decorator registration ✅
- `test_tool_decorator_no_name` — Auto-naming ✅
- `test_register_tool_auto_capability` — Auto capability registration ✅
- `test_register_tool_no_capability_registry` — No CR mode ✅
- `test_tool_decorator_auto_capability` — Decorator + CR ✅
- `test_parameter_validation_valid` — Valid params pass ✅
- `test_parameter_validation_invalid_type` — Wrong type rejected ✅
- `test_parameter_validation_missing_required` — Missing required rejected ✅
- `test_parameter_validation_no_schema` — No schema passes ✅
- `test_execute_timeout` — Timeout enforced ✅
- `test_event_publication_on_started` — `tool:started` event ✅
- `test_event_publication_on_completed` — `tool:completed` event ✅
- `test_event_publication_on_failed` — `tool:failed` event ✅
- `test_event_publication_on_timeout` — `tool:timeout` event ✅
- `test_di_registration` — DI container registration ✅
- `test_di_registration_with_event_bus` — DI with event bus ✅
- `test_exception_types` — Typed exception hierarchy ✅
- `test_unregister_tool` — Tool unregistered ✅
- `test_execute_tool_exception_wraps_error` — Exceptions wrapped ✅
- `test_execute_tool_with_contract_result` — ToolResult returned ✅
- `test_validation_error_does_not_execute` — Invalid not executed ✅
- `test_tool_timeout_error_sets_duration` — Duration measured ✅

**Acceptance Criteria:**
- Tools registerable and executable ✅
- JSON Schema parameter validation works ✅
- Timeout enforced via `asyncio.wait_for()` ✅
- Event Bus integration publishes lifecycle events ✅
- DI Container registration works ✅
- Typed exceptions with proper error codes ✅
- Backward-compatible: existing tool implementations unchanged ✅
- All 27 tests pass, 0 lint errors ✅

**Risks:**
- File system operations need careful testing

**Estimated Effort:** 3 days

**Completed:** 2026-07-21 — ~250 lines core, 27 unit tests, 0 lint errors, 189 core tests passing

---

### Sprint 9: Capability Registry

**Objective:** Implement capability-based discovery layer

**Scope:** Capability registration, discovery, versioning, conflict resolution

**Dependencies:** Sprint 8

**Deliverables:**
- `src/backend/aios/core/capability_registry.py`
- Capability registration
- Capability discovery
- Conflict resolution
- Version management
- API endpoints

**Technical Tasks:**
1. Implement `Capability` dataclass:
   - `id`, `name`, `description`
   - `provider_type`, `provider_id`
   - `parameters`, `returns`
   - `permission_level`, `tags`, `version`
   - `quality` (float 0.0-1.0)
2. Implement `CapabilityRegistry`:
   - `register_capability(capability)`
   - `register_provider(provider_type, provider)`
   - `find_capability(query, context) -> list[Capability]`
   - `find_best_match(query, context) -> Capability`
   - `list_capabilities(tag) -> list[Capability]`
   - `search_capabilities(query) -> list[Capability]`
3. Implement conflict resolution:
   - Quality score (weight 0.4)
   - Context match (weight 0.3)
   - Version (weight 0.2)
   - Permission level (weight 0.1)
4. Implement capability versioning
5. Implement API endpoints:
   - `GET /api/v1/capabilities`
   - `POST /api/v1/capabilities/search`
6. Write unit and integration tests

**Tests:**
- `test_register_capability` — Capability registered
- `test_find_capability` — Capability found
- `test_find_best_match` — Best match returned
- `test_conflict_resolution` — Conflicts resolved correctly
- `test_versioning` — Version support
- `test_no_match` — Empty result for unknown

**Acceptance Criteria:**
- Capabilities registerable
- Discovery works
- Conflicts resolved
- Versioning supported
- Planner can query capabilities

**Risks:**
- None

**Estimated Effort:** 2 days

---

### Sprint 10: Memory System

**Objective:** Implement short-term, long-term, and semantic memory

**Scope:** Memory storage, semantic search, conversation history, workspace memory

**Dependencies:** Sprint 9

**Deliverables:**
- `src/backend/aios/core/memory_system.py`
- `src/backend/aios/models/memory.py`
- Short-term memory (in-memory)
- Long-term memory (SQLite + embeddings)
- Semantic search
- Conversation history
- Memory API endpoints

**Technical Tasks:**
1. Implement `Memory` dataclass:
   - `id`, `type` (fact, preference, learning, pattern)
   - `content`, `embedding`, `importance`
   - `source`, `conversation_id`
   - `timestamp`, `accessed_at`, `access_count`
2. Implement `ShortTermMemory`:
   - Session-based, in-memory
   - Conversation context
   - Active tools, current plan
3. Implement `LongTermMemory`:
   - SQLite persistence
   - Embedding-based storage
   - Importance calculation
4. Implement `SemanticSearch`:
   - Embedding generation via AI Router
   - Cosine similarity search
   - Hybrid (keyword + semantic)
5. Implement `MemorySystem`:
   - `store(memory)`, `search(query)`, `recall(memory_id)`
   - `forget(memory_id)`, `get_conversation(conversation_id)`
6. Implement conversation history management
7. Implement API endpoints:
   - `POST /api/v1/memory/search`
   - `POST /api/v1/memory/store`
8. Write unit and integration tests

**Tests:**
- `test_store_memory` — Memory stored
- `test_search_memory` — Memory found
- `test_recall_memory` — Memory retrieved
- `test_forget_memory` — Memory deleted
- `test_importance_scoring` — Importance calculated
- `test_conversation_history` — History retrieved

**Acceptance Criteria:**
- Memories stored and retrieved
- Semantic search works
- Conversation history persisted
- Importance scoring works
- API endpoints functional

**Risks:**
- Embedding model may add latency

**Estimated Effort:** 3 days

---

### Sprint 11: Planner ✅

**Objective:** Implement task decomposition and execution

**Scope:** Task decomposition, execution graph, validation, recovery, plan persistence

**Dependencies:** Sprint 9, Sprint 10

**Deliverables:**
- `src/backend/aios/core/planner.py` ✅
- Task decomposition ✅
- Execution graph with topological sort ✅
- Plan validation with cycle detection ✅
- Recovery strategies (skip dependents) ✅
- Plan persistence (in-memory) ✅

**Technical Tasks:**
1. Implement `Plan` dataclass ✅
2. Implement `Step` dataclass with `StepStatus.TIMEOUT` ✅
3. Implement `Planner`:
   - `create_plan(request, context) -> Plan` ✅
   - `execute_plan(plan, tool_manager) -> Plan` with parallel groups and event publishing ✅
   - `validate_plan(plan) -> PlanValidation` with cycle detection ✅
   - `recover_plan(plan, failed_step) -> Plan` removes dependent steps ✅
   - `_topological_sort_inner()` — Kahn's algorithm returning parallel groups ✅
   - `_execute_step(step, tool_manager)` — `asyncio.wait_for` with timeout enforcement ✅
4. Implement execution graph:
   - Topological sort with parallel group execution ✅
   - Steps with no dependency chain run concurrently via `asyncio.gather` ✅
5. Implement validation:
   - Step timeout (30s default) enforced via `asyncio.wait_for` ✅
   - Unknown dependency detection ✅
   - Cycle detection ✅
6. Implement recovery strategies:
   - Step failure → dependent steps marked SKIPPED ✅
   - Timeout → step marked TIMEOUT, dependents skipped ✅
7. Implement plan persistence (in-memory `dict`, no SQLite dependency) ✅
   - `get_plan(plan_id)` ✅
   - `list_plans(limit)` ✅
   - `get_plan_result(plan_id)` ✅
8. Write unit tests ✅ — 26 tests (7 original + 19 new)

**Tests:**
- `test_create_plan` — Plan created from request ✅
- `test_execute_plan` — Steps executed in order ✅
- `test_execute_plan_with_tool_manager` — Tool manager integration ✅
- `test_execute_plan_tool_not_found` — Tool not found handled ✅
- `test_execute_plan_timeout` — Timeout enforced ✅
- `test_execute_plan_parallel` — Independent steps run in parallel ✅
- `test_execute_plan_dependency_skipped` — Failed step skips dependents ✅
- `test_execute_plan_already_running` — Re-execution guard ✅
- `test_execute_plan_empty` — Empty plan handled ✅
- `test_execute_plan_unknown_dependency` — Unknown dep rejected ✅
- `test_plan_validation` — Invalid plan rejected ✅
- `test_recovery` — Recovery on failure ✅
- `test_recover_plan_removes_dependents` — Dependent steps removed ✅
- `test_topological_sort_simple` — Simple linear sort ✅
- `test_topological_sort_parallel` — Parallel groups correct ✅
- `test_topological_sort_cycle` — Cycle detected ✅
- `test_validate_plan` — Validation passes ✅
- `test_validate_plan_unknown_dependency` — Unknown dep caught ✅
- `test_get_plan` — Plan retrieval ✅
- `test_get_plan_result` — Result retrieval ✅
- `test_get_plan_result_not_found` — Not found handled ✅
- `test_list_plans` — Plan listing ✅
- `test_event_bus_integration` — Events published on lifecycle ✅

**Acceptance Criteria:**
- Plans created and executed ✅
- Steps decomposed correctly ✅
- Recovery strategies work ✅
- Plans persisted (in-memory) ✅
- No direct tool knowledge ✅
- Topological sort with parallel groups ✅
- Timeout enforcement ✅
- Event bus integration ✅

**Risks:**
- AI response parsing may need tuning

**Estimated Effort:** 3 days

**Completed:** 2026-07-21 — ~340 lines, 26 unit tests, 0 lint errors

---

### Sprint 12: Context Engine ✅

**Objective:** Implement context tracking and awareness

**Scope:** Active window monitoring, project detection, activity inference, Event Bus integration, MemoryStore persistence

**Dependencies:** Sprint 13 (Windows Adapter)

**Deliverables:**
- `src/backend/aios/core/context/models.py` ✅ — `Context`, `ProjectInfo`, `ActivityType` dataclasses
- `src/backend/aios/core/context/project_detector.py` ✅ — Parent-directory scan for 12 project markers
- `src/backend/aios/core/context/activity_detector.py` ✅ — Activity inference from app name/window title
- `src/backend/aios/core/context/engine.py` ✅ — `ContextEngine` with async polling, event publishing, MemoryStore integration
- `src/backend/aios/core/context/__init__.py` ✅ — Clean public API exports
- `src/backend/aios/core/context_engine.py` ✅ — Legacy re-exports from package

**Technical Tasks:**
1. Implement `Context` dataclass:
   - `active_app`, `active_window`, `active_file` ✅
   - `project_path`, `project_type` → `ProjectInfo` nested dataclass ✅
   - `recent_files`, `open_applications` ✅
   - `activity` (ActivityType enum), `timestamp` ✅
   - `changed_since()` change-diff method ✅
2. Implement `ContextEngine`:
   - `get_current_context() -> Context` ✅
   - `get_active_app() -> str` ✅
   - `get_active_file() -> Optional[str]` ✅
   - `detect_project() -> Optional[ProjectInfo]` ✅
   - `get_recent_activity(minutes) -> list[Context]` ✅
   - `poll_now() -> Context` ✅
   - `start()` / `stop()` lifecycle ✅
3. Implement polling loop (every 2.0s, configurable via `context_poll_interval`) ✅
4. Implement project detection:
   - Check for `.git`, `package.json`, `pyproject.toml`, `Cargo.toml`, `go.mod`, etc. (12 markers) ✅
5. Implement activity inference:
   - ActivityType: CODING, BROWSING, WRITING, OFFICE, IDLE, UNKNOWN ✅
   - Categorized app sets (IDE_APPS, BROWSER_APPS, OFFICE_APPS, TERMINAL_APPS) ✅
   - File extraction from IDE/terminal window titles ✅
6. Implement context publish on changes:
   - Events: `context:changed`, `context:project_changed`, `context:file_changed`, `context:activity_changed`, `context:application_changed` ✅
7. Implement MemoryStore integration:
   - `MemoryStore.create_node()` for non-idle observations ✅
8. Implement DI Container registration:
   - `ContextEngine.register_in_container()` ✅
9. Write unit tests ✅ — 85 tests

**Tests:**
- `test_get_context` — Context returned ✅
- `test_active_app` — App detected ✅
- `test_project_detection` — Project found ✅
- `test_context_changes` — Events published on change ✅
- `test_recent_activity` — Activity tracked ✅
- `test_model_changed_since` — Change detection correct ✅
- `test_project_detector_markers` — 12 project markers supported ✅
- `test_activity_detection_categories` — All activity types detected ✅
- `test_engine_lifecycle` — start/stop/idempotent/lifecycle events ✅
- `test_engine_events` — All 5 event types published on change ✅
- `test_engine_memory` — Memory stored for non-idle, skipped for idle ✅
- `test_engine_public_api` — All public methods work ✅
- `test_di_container` — Registration and resolution ✅

**Acceptance Criteria:**
- Context detected and updated ✅
- Projects detected from 12 marker types ✅
- Activity inferred from app/window name ✅
- Changes published via Event Bus (5 event types) ✅
- Memory persisted via MemoryStore for non-idle observations ✅
- Polling interval configurable via settings ✅
- DI Container registration works ✅
- Depends only on WindowsAdapter (no direct Win32 calls) ✅
- 85 tests passing, 0 lint errors ✅

**Risks:**
- Window title parsing may be unreliable

**Estimated Effort:** 2 days

**Completed:** 2026-07-21 — 6 files, ~400 lines core, 85 unit tests, 0 lint errors

---

### Sprint 13: Windows Adapter ✅

**Objective:** Implement OS abstraction layer

**Scope:** File system, process management, system info, UI automation, clipboard, validation, typed exceptions, adapter facade with permission-gating and event-publishing

**Dependencies:** Sprint 8

**Deliverables:**
- `src/backend/aios/core/windows/exceptions.py` ✅ — 13 typed exceptions
- `src/backend/aios/core/windows/validation.py` ✅ — Path/pid/name/extension/page validation with security checks
- `src/backend/aios/core/windows/clipboard.py` ✅ — get/set/clear text via pyperclip
- `src/backend/aios/core/windows/filesystem.py` ✅ — search/read/write/delete/move/copy/metadata/exists
- `src/backend/aios/core/windows/process.py` ✅ — list/get/find/start/terminate/kill via psutil/subprocess
- `src/backend/aios/core/windows/active_window.py` ✅ — get_active_window/search_by_title/list_titles via pygetwindow
- `src/backend/aios/core/windows/monitor.py` ✅ — monitors/cursor/screen_size via screeninfo/pyautogui
- `src/backend/aios/core/windows/ui_automation.py` ✅ — click/type/press_key/hotkey/mouse/scroll/drag/screenshot
- `src/backend/aios/core/windows/system_info.py` ✅ — OS/CPU/RAM/disk/network/uptime via psutil
- `src/backend/aios/core/windows/adapter.py` ✅ — `WindowsAdapter(BaseAdapter)` facade
- `src/backend/aios/core/windows/__init__.py` ✅ — clean public API exports

**Technical Tasks:**
1. Implement `BaseAdapter` abstract class ✅
2. Implement `WindowsAdapter`:
   - `search_files(pattern, path) -> list[FileInfo]` ✅
   - `read_file(path) -> str` ✅
   - `write_file(path, content)` ✅
   - `delete_file(path)` ✅
   - `create_directory(path)` ✅
   - `list_processes() -> list[ProcessInfo]` ✅
   - `get_process_info(pid) -> ProcessInfo` ✅
   - `start_process(command) -> int` ✅
   - `kill_process(pid)` ✅
   - `get_system_info() -> SystemInfo` ✅
   - `get_disk_usage() -> list[DiskInfo]` ✅
   - `get_active_window() -> WindowInfo` ✅
   - `get_screenshot() -> bytes` ✅
   - `click(x, y)` ✅
   - `type_text(text)` ✅
   - `get_clipboard() -> str` ✅
   - `set_clipboard(text)` ✅
3. Implement input validation ✅ — `validation.py` with security checks (blocked system dirs, traversal detection, allowed extensions)
4. Implement error handling for all calls ✅ — 13 typed exception classes
5. Implement permission-gated facade with event publishing ✅ — PermissionLevel READ/SAFE/WORKSPACE/SENSITIVE, events: clipboard:changed, file:read/changed, process:started/stopped, active_window:changed
6. Implement DI Container registration ✅ — `WindowsAdapter.register_in_container()`
7. Write unit tests ✅ — 65 tests

**Tests:**
- `test_search_files` — Files found ✅
- `test_read_write_file` — File read/write ✅
- `test_list_processes` — Processes listed ✅
- `test_system_info` — System info returned ✅
- `test_screenshot` — Screenshot captured ✅
- `test_clipboard` — Clipboard read/write ✅
- `test_permissions` — Permission gating works ✅
- `test_events` — Events published on operations ✅
- `test_di_registration` — DI registration works ✅
- `test_validation` — Input validation correct ✅
- `test_exceptions` — All exceptions typed ✅

**Acceptance Criteria:**
- All file system operations work ✅
- Process management works ✅
- System info accessible ✅
- UI automation functional ✅
- Clipboard accessible ✅
- No direct Windows modification ✅
- Permission-gated operations ✅
- Event publishing on lifecycle ✅
- DI Container registration ✅
- Input validation with security checks ✅
- Typed exception hierarchy ✅
- 65 tests passing, 0 lint errors ✅

**Risks:**
- Screenshot capture needs permission

**Estimated Effort:** 3 days

**Completed:** 2026-07-21 — 11 files, ~950 lines core, 65 unit tests, 0 lint errors

---

### Sprint 14: Chat UI

**Objective:** Implement the chat interface

**Scope:** React UI, chat components, command palette, settings, permissions UI

**Dependencies:** Sprint 5, Sprint 6

**Deliverables:**
- `src/frontend/src/App.tsx`
- `src/frontend/src/components/chat/ChatWindow.tsx`
- `src/frontend/src/components/chat/MessageList.tsx`
- `src/frontend/src/components/chat/MessageInput.tsx`
- `src/frontend/src/components/command/CommandPalette.tsx`
- `src/frontend/src/components/permissions/PermissionDialog.tsx`
- `src/frontend/src/components/settings/SettingsPanel.tsx`
- API client services
- State management stores

**Technical Tasks:**
1. Set up React + Vite + Tailwind
2. Implement `App.tsx` — Root layout
3. Implement `ChatWindow` — Main chat area
4. Implement `MessageList` — Message display
5. Implement `MessageInput` — Text input
6. Implement `CommandPalette` — Ctrl+K palette
7. Implement `PermissionDialog` — Permission requests
8. Implement `SettingsPanel` — Configuration UI
9. Implement `ApiClient` service — Backend communication
10. Implement SSE streaming for chat
11. Implement state management
12. Implement dark/light theme
13. Write frontend tests

**Tests:**
- `test_chat_send` — Message sent
- `test_chat_receive` — Response received
- `test_command_palette` — Commands searchable
- `test_permission_dialog` — Dialog displayed
- `test_settings_panel` — Settings load/save
- `test_theme_toggle` — Theme switches

**Acceptance Criteria:**
- Chat interface functional
- Messages sent and received
- Command palette works
- Permission dialogs displayed
- Settings configurable
- Dark/light theme

**Risks:**
- SSE streaming may need reconnection logic

**Estimated Effort:** 4 days

---

### Sprint 15: Conversation Manager

**Objective:** Implement conversation lifecycle management

**Scope:** Chat, voice, hybrid modes, conversation persistence, context attachment

**Dependencies:** Sprint 14

**Deliverables:**
- `src/backend/aios/core/conversation.py`
- Message routing
- Mode switching
- Context attachment
- API endpoints

**Technical Tasks:**
1. Implement `ConversationSystem`:
   - `send_message(content, mode) -> Message`
   - `stream_message(content) -> AsyncIterator[StreamEvent]`
   - `get_history(conversation_id) -> list[Message]`
   - `create_conversation(title) -> Conversation`
   - `delete_conversation(conversation_id)`
   - `switch_mode(mode)`
2. Implement message routing:
   - Chat mode → direct response
   - Voice mode → STT → response → TTS
   - Hybrid mode → switchable mid-conversation
3. Implement context attachment:
   - Attach context to every message
4. Implement API endpoints:
   - `POST /api/v1/chat/message`
   - `GET /api/v1/chat/stream`
   - `GET /api/v1/chat/history`
5. Write unit and integration tests

**Tests:**
- `test_send_message` — Message sent
- `test_stream_message` — Stream received
- `test_conversation_create` — Conversation created
- `test_conversation_delete` — Conversation deleted
- `test_mode_switch` — Mode switches correctly
- `test_history` — History returned

**Acceptance Criteria:**
- Messages sent and streamed
- Conversations managed
- Modes switchable
- Context attached
- API endpoints functional

**Risks:**
- None

**Estimated Effort:** 2 days

---

### Sprint 16: Voice

**Objective:** Implement voice input and output

**Scope:** Speech-to-text, text-to-speech, voice activation

**Dependencies:** Sprint 15

**Deliverables:**
- Voice input (STT)
- Voice output (TTS)
- Wake word detection
- Voice mode integration

**Technical Tasks:**
1. Implement STT using speech_recognition or Whisper
2. Implement TTS using pyttsx3 or Edge TTS
3. Implement wake word detection
4. Implement voice mode in Conversation Manager
5. Implement microphone management
6. Write unit tests

**Tests:**
- `test_stt` — Speech recognized
- `test_tts` — Speech generated
- `test_voice_mode` — Voice mode active
- `test_wake_word` — Wake word detected

**Acceptance Criteria:**
- Voice input works
- Voice output works
- Wake word activates AIOS
- Voice mode functional

**Risks:**
- Microphone permission needed
- STT accuracy may vary

**Estimated Effort:** 3 days

---

### Sprint 17: Vision System

**Objective:** Implement screen capture and OCR

**Scope:** Screenshot capture, OCR, UI element detection

**Dependencies:** Sprint 13

**Deliverables:**
- `src/backend/aios/vision/screenshot.py`
- `src/backend/aios/vision/ocr.py`
- `src/backend/aios/vision/ui_understanding.py`
- Screenshot capture
- Text extraction
- UI element detection

**Technical Tasks:**
1. Implement screenshot capture via PyAutoGUI
2. Implement OCR via Tesseract
3. Implement UI element detection via AI vision
4. Implement `VisionSystem`:
   - `capture_screen(region) -> Image`
   - `extract_text(image) -> str`
   - `find_element(image, description) -> Element`
   - `detect_ui_elements(image) -> list[UIElement]`
5. Register vision capabilities with Capability Registry
6. Write unit tests

**Tests:**
- `test_capture_screen` — Screenshot captured
- `test_extract_text` — Text extracted
- `test_detect_elements` — Elements detected
- `test_find_element` — Element found

**Acceptance Criteria:**
- Screenshots captured
- Text extracted via OCR
- UI elements detected
- Capabilities registered

**Risks:**
- Tesseract installation required

**Estimated Effort:** 3 days

---

### Sprint 18: Browser Automation

**Objective:** Implement web automation

**Scope:** Web search, navigation, content extraction

**Dependencies:** Sprint 13

**Deliverables:**
- `src/backend/aios/tools/browser.py`
- Web search
- Page navigation
- Content extraction
- Capability registration

**Technical Tasks:**
1. Implement Playwright-based browser automation
2. Implement web search tool
3. Implement page navigation tool
4. Implement content extraction tool
5. Register browser capabilities
6. Write unit tests

**Tests:**
- `test_web_search` — Search returns results
- `test_page_navigate` — Navigation works
- `test_content_extract` — Content extracted
- `test_headless_mode` — Headless works

**Acceptance Criteria:**
- Web search works
- Navigation works
- Content extraction works
- Capabilities registered

**Risks:**
- Playwright browser installation needed

**Estimated Effort:** 2 days

---

### Sprint 19: Plugin System

**Objective:** Implement third-party plugin support

**Scope:** Plugin manager, sandbox, manifest validation, SDK

**Dependencies:** Sprint 9

**Deliverables:**
- `src/backend/aios/plugins/plugin_manager.py`
- `src/backend/aios/plugins/sandbox.py`
- Plugin manifest validation
- Sandboxed execution
- Plugin lifecycle
- Plugin SDK

**Technical Tasks:**
1. Implement `PluginManifest` validation:
   - `id`, `name`, `version`, `min_aios_version`
   - `author`, `description`, `permissions`
   - `tools`, `events`, `lifecycle`
2. Implement `PluginManager`:
   - `scan_plugins() -> list[PluginManifest]`
   - `load_plugin(manifest) -> Plugin`
   - `unload_plugin(plugin_id)`
   - `get_plugin(plugin_id) -> PluginManifest`
   - `list_plugins() -> list[PluginManifest]`
3. Implement `Sandbox`:
   - Isolated subprocess execution
   - Resource limits (memory, CPU, time)
   - No direct file system access
   - No network access without permission
4. Implement `PluginAPI`:
   - `register_tool`, `subscribe`, `publish`
   - `store_memory`, `search_memory`
   - `show_notification`, `show_dialog`
   - `get_config`, `set_config`
5. Implement plugin lifecycle:
   - Discovered → Validated → Loaded → Active → Unloaded
6. Implement API endpoints:
   - `GET /api/v1/plugins`
   - `POST /api/v1/plugins/install`
7. Write unit and integration tests

**Tests:**
- `test_plugin_scan` — Plugins discovered
- `test_plugin_load` — Plugin loaded
- `test_plugin_unload` — Plugin unloaded
- `test_sandbox_execution` — Sandbox works
- `test_manifest_validation` — Invalid manifest rejected
- `test_plugin_permissions` — Permissions enforced

**Acceptance Criteria:**
- Plugins discoverable and loadable
- Sandboxed execution works
- Permissions enforced
- SDK functional
- API endpoints work

**Risks:**
- Sandbox security needs thorough testing

**Estimated Effort:** 4 days

---

### Sprint 20: Developer Tools

**Objective:** Implement developer tooling

**Scope:** Hot reload, debug console, module inspector, health dashboard

**Dependencies:** Sprint 19

**Deliverables:**
- Hot reload support
- Debug console
- Module inspector
- Health dashboard

**Technical Tasks:**
1. Implement hot reload for Python modules
2. Implement debug console UI
3. Implement module inspector
4. Implement health dashboard
5. Write tests

**Tests:**
- `test_hot_reload` — Module reloads
- `test_debug_console` — Console works
- `test_health_dashboard` — Dashboard renders

**Acceptance Criteria:**
- Hot reload works during development
- Debug console functional
- Module inspector shows state
- Health dashboard accessible

**Risks:**
- None

**Estimated Effort:** 2 days

---

### Sprint 21: Eve Launcher ✅

**Objective:** Transform Eve from a development project into a desktop application that launches with a single click — no terminal required.

**Scope:** Splash screen, system tray, process manager, health monitor, startup/shutdown orchestrator, first-run wizard, auto-update placeholder, configuration management, logging, root entry point.

**Dependencies:** All previous sprints

**Location:** `launcher/`

**Deliverables:**
- `launcher/launcher.py` — Main orchestrator, lifecycle management, auto-recovery ✅
- `launcher/config.py` — `LauncherConfig` JSON-backed Pydantic-based configuration ✅
- `launcher/logger.py` — File + console logging with rotation, `open_log_folder()` ✅
- `launcher/splash.py` — Tkinter startup progress window ✅
- `launcher/process_manager.py` — `ProcessManager`, `ManagedProcess` subprocess lifecycle ✅
- `launcher/health_checker.py` — `HealthChecker`, `ServiceHealth`, `ProviderStatus` health polling ✅
- `launcher/startup.py` — `StartupOrchestrator` sequential service launch ✅
- `launcher/shutdown.py` — `ShutdownManager` graceful resource release ✅
- `launcher/tray.py` — `TrayManager` system tray with menu ✅
- `launcher/first_run.py` — `FirstRunWizard` Tkinter setup wizard ✅
- `launcher/updater.py` — `Updater`, `UpdateInfo` auto-update placeholder ✅
- `eve.py` — Root entry point (`python eve.py`) ✅
- `eve.bat` — Windows double-click launcher ✅

**Technical Tasks:**
1. Design launcher architecture (modules, responsibilities, interfaces) ✅
2. Implement `LauncherConfig` — JSON-backed, `backend_url`/`frontend_url`/`health_url` computed properties, `is_first_run` ✅
3. Implement `setup_launcher_logging()` — file + console handlers, rotation, `open_log_folder()` ✅
4. Implement `SplashScreen` — Tkinter window, `update_status()`, `set_ready()`, `close()` ✅
5. Implement `ProcessManager` — `start(name, *args)`, `stop(name, timeout)`, `stop_all()`, `start_backend()`, `start_frontend()`, `is_alive()`, `get()` ✅
6. Implement `HealthChecker` — polls backend health endpoint, frontend URL, AI providers (gemini/groq/openrouter/ollama) ✅
7. Implement `StartupOrchestrator` — backemd → health → frontend → AI providers → init tools ✅
8. Implement `ShutdownManager` — health monitor → frontend → backend ✅
9. Implement `TrayManager` — pystray icon, Open/Restart/DevTools/Health/Logs/Settings/Exit menu ✅
10. Implement `FirstRunWizard` — Tkinter provider/API key/theme selection ✅
11. Implement `Updater` placeholder — GitHub releases stub ✅
12. Implement `main_async()` orchestrator tying all modules together ✅
13. Create `eve.py` and `eve.bat` root entry points ✅
14. Write 31 unit tests ✅
15. Update docs: `11_Project_Status.md`, `30-IMPLEMENTATION_PLAN.md`, `LAUNCHER_ARCHITECTURE.md` ✅

**Tests:** (31 tests)
- `test_config.py` — defaults, set/get, save/load, first_run, all_data (5 tests) ✅
- `test_logger.py` — setup, log levels, singleton (3 tests) ✅
- `test_health_checker.py` — services, providers, backend down, AI provider missing key/Ollama offline, monitor lifecycle, restart check, backend modules (10 tests) ✅
- `test_process_manager.py` — start, get, stop nonexistent, stop all, ManagedProcess properties, is_alive (6 tests) ✅
- `test_startup.py` — wait_for_url timeout, startup backend fails (2 tests) ✅
- `test_updater.py` — initial state, check, download, apply, UpdateInfo defaults (5 tests) ✅

**Acceptance Criteria:**
- Launcher starts backend (`python -m aios.main`) on port 8456 ✅
- Launcher starts frontend (`npm run dev`) on port 5173 ✅
- Splash screen shows progress during startup ✅
- System tray with Open/Restart/DevTools/Health/Logs/Settings/Exit ✅
- Health monitor polls backend health endpoint (`/api/v1/system/health`) ✅
- AI providers checked but don't block startup if unavailable ✅
- First-run wizard shown on initial launch ✅
- Configuration stored at `~/.eve/launcher_config.json` ✅
- Logs stored at `~/.eve/logs/launcher.log` ✅
- Closing window minimizes to tray, does not quit ✅
- Auto-recovery: backend/frontend restarted on health failure (max 3 attempts) ✅
- Graceful shutdown stops frontend → backend → health monitor ✅
- All existing tests still pass ✅
- 31 new launcher tests passing ✅

**Key Design Decisions:**
- Unavailable AI providers do NOT block startup — only disabled in UI
- Closing main window minimizes to tray, does NOT quit
- pystray required for system tray; handled gracefully if missing
- Tkinter for splash/first-run (stdlib, no extra dependency)
- Backend health endpoint at `/api/v1/system/health`
- All asyncio — single event loop manages subprocesses, health polling, lifecycle

**Risks:**
- pystray may not be installed → tray functionality gracefully degraded
- Tkinter may not be available → splash falls back to console logging

**Estimated Effort:** 2 days

### Sprint 1.5 — Launcher Refactor (Service-Oriented Architecture)

**Objective:** Refactor the monolithic launcher into a reusable orchestration engine (LauncherService) that does NOT own the UI, preparing for future Tauri native shell integration.

**Scope:** Service-oriented architecture, lifecycle events, DI-friendly design, backward-compat wrappers, FrontendProtocol abstraction

**Dependencies:** Sprint 21

**Deliverables:**
- `launcher/launcher_service.py` — `LauncherService` main orchestration API: `initialize()`, `start()`, `stop()`, `restart()`, `shutdown()`, `status()`, `health()`, `on_event()`, `off_event()`, `launch_frontend()`, `open_devtools()`, `open_health_dashboard()`, `open_settings()` ✅
- `launcher/launcher_api.py` — `LauncherStatus` dataclass (state, version, services, providers, uptime), `LauncherAPI` consumable by Tauri ✅
- `launcher/launcher_events.py` — 18 typed lifecycle event constants, `LauncherEvent` dataclass (id, type, data, timestamp), `EventHandler` type alias ✅
- `launcher/services/__init__.py` — service package ✅
- `launcher/services/config_service.py` — `ConfigService` JSON-backed settings ✅
- `launcher/services/logger_service.py` — `LoggerService` file + console logging ✅
- `launcher/services/process_service.py` — `ProcessService` (ProcessManager alias) subprocess lifecycle ✅
- `launcher/services/backend_service.py` — `BackendService` backend Python process ✅
- `launcher/services/frontend_service.py` — `BrowserFrontendService` implementing `FrontendProtocol` ✅
- `launcher/services/health_service.py` — `HealthService` health polling + event emission ✅
- `launcher/services/provider_service.py` — `ProviderService` AI provider connectivity ✅
- `launcher/services/tray_service.py` — `TrayService` system tray (abstracted) ✅
- `launcher/services/startup_service.py` — `StartupService` sequential launch ✅
- `launcher/services/shutdown_service.py` — `ShutdownService` graceful teardown ✅
- `launcher/launcher.py` — `DesktopLauncher` thin UI wrapper (splash + tray + first-run wizard), delegating to LauncherService ✅
- Backward-compat wrappers for all old modules: `config.py`, `logger.py`, `process_manager.py`, `health_checker.py`, `startup.py`, `shutdown.py`, `tray.py` ✅
- Updated `launcher/__init__.py` → version 1.1.0 ✅
- `eve.py` — unchanged top-level API, delegates to `launcher.launcher.main()` ✅

**Technical Tasks:**
1. Design service interfaces (ConfigService, LoggerService, ProcessService, etc.) with constructor injection ✅
2. Implement `LauncherEvent` dataclass with UUID + timestamp + type + data ✅
3. Define 18 lifecycle events (launcher:starting/ready/stopping/stopped/error, backend:started/stopped/failed/degraded, frontend:started/stopped/failed, provider:connected/disconnected, service:health_changed, shutdown:requested/completed, restart:requested/completed) ✅
4. Implement `FrontendProtocol` abstract interface (start/stop/restart/is_alive/get_type) ✅
5. Implement `BrowserFrontendService` implementing FrontendProtocol (npm run dev) ✅
6. Implement `LauncherService` orchestrator:
   - initialize() — lazy service creation, config/logger setup ✅
   - start() — startup sequence + health monitoring, guard for uninitialized ✅
   - stop() — stop health monitor only ✅
   - shutdown() — full teardown (tray → health → frontend → backend) ✅
   - restart() — stop + start ✅
   - status() → LauncherStatus dataclass ✅
   - health() → dict of health check results ✅
   - launch_frontend() / open_devtools() / open_health_dashboard() / open_settings() ✅
   - on_event() / off_event() — subscribe/unsubscribe with UUID subscription IDs ✅
7. Implement `DesktopLauncher` thin wrapper that adds splash/tray/wizard UI, delegates to LauncherService ✅
8. Replace all old module files with backward-compat re-export wrappers ✅
9. Write 48 new tests ✅
10. Update LAUNCHER_ARCHITECTURE.md, 11_Project_Status.md, 30-IMPLEMENTATION_PLAN.md ✅

**Tests:** (48 new tests)

`tests/launcher/test_launcher_service.py` — 13 tests:
- `test_initialize` — Service initializes correctly ✅
- `test_start` — Services start correctly ✅
- `test_stop` — Services stop correctly ✅
- `test_full_lifecycle` — Full init/start/stop cycle ✅
- `test_shutdown` — Full shutdown ✅
- `test_restart` — Restart cycle ✅
- `test_double_start` — Idempotent start ✅
- `test_events_subscribe` — Event subscription works ✅
- `test_events_unsubscribe` — Event unsubscription works ✅
- `test_status` — Status returns correct state ✅
- `test_status_after_start` — Status shows running services ✅
- `test_health` — Health check results ✅
- `test_state_initialized` — State machine transitions ✅

`tests/launcher/test_services.py` — 25 tests:
- ConfigService (3): create, set, save/load ✅
- LoggerService (2): setup, open_log_folder ✅
- ProcessService (3): start, get, stop ✅
- BackendService (2): start, stop ✅
- FrontendService (3): start, stop, protocol adherence ✅
- HealthService (4): get_status, check, monitoring lifecycle, bad URL ✅
- ProviderService (2): connected_providers, check_all ✅
- StartupService (2): run, missing process ✅
- ShutdownService (2): shutdown, missing process ✅
- LauncherAPI (2): constructor, status ✅

`tests/launcher/test_events.py` — 10 tests:
- Event constants (6): READY/STOPPING/ERROR/BACKEND/FRONTEND/PROVIDER exist ✅
- LauncherEvent (4): construction, defaults, data, str UUID ✅

**Remaining (from Sprint 21 — 31 tests):**
- `test_config.py` — 5 tests (defaults, set/get, save/load, first_run, all_data) ✅
- `test_logger.py` — 3 tests (setup, log levels, singleton) ✅
- `test_health_checker.py` — 10 tests ✅
- `test_process_manager.py` — 6 tests ✅
- `test_startup.py` — 2 tests ✅
- `test_updater.py` — 5 tests ✅

**Acceptance Criteria (Sprint 1.5 additions):**
- LauncherService is UI-agnostic (no browser open on start) ✅
- FrontendService abstracted via FrontendProtocol ✅
- TrayService abstracted for future Tauri replacement ✅
- All services accept dependencies via constructor injection (no global state) ✅
- 18 lifecycle events defined and testable ✅
- Old import paths all preserved via backward-compat wrappers ✅
- All 31 old tests pass through compat layer ✅
- 79 total launcher tests passing ✅
- Full test suite: 1042 passed, 0 failures, 0 lint errors ✅

**Estimated Effort:** 2 days

**Completed:** 2026-07-22 — 10 service modules, LauncherService, events system, status API, 48 new tests, 79 total launcher tests, 0 lint errors

---

### Sprint 2 — Tauri Desktop Shell

**Objective:** Replace browser-based frontend with a native Windows desktop application using Tauri v2.

**Scope:** Tauri project setup, Python launcher integration, native window, system tray, native APIs, packaging, documentation

**Dependencies:** Sprint 1.5 (LauncherService, FrontendProtocol, TrayProtocol, LauncherAPI)

**Deliverables:**
- `desktop/package.json` — npm project with `@tauri-apps/cli` ✅
- `desktop/src-tauri/Cargo.toml` — Rust deps (tauri v2, 6 plugins) ✅
- `desktop/src-tauri/tauri.conf.json` — Points to existing React frontend, window config, bundle config ✅
- `desktop/src-tauri/capabilities/default.json` — Permission capabilities for all plugins ✅
- `desktop/src-tauri/build.rs` — Tauri build script ✅
- `desktop/src-tauri/src/main.rs` — Rust entry point (windows_subsystem = "windows") ✅
- `desktop/src-tauri/src/lib.rs` — App setup: plugin registration, system tray, window event handlers ✅
- `desktop/src-tauri/src/commands.rs` — 8 Tauri commands (get_status, get_health, restart_backend, shutdown, show_notification, open_url, get/set_app_config) ✅
- `desktop/src-tauri/src/launcher.rs` — Python child process management, stdin/stdout JSON protocol, ready detection ✅
- `desktop/src-tauri/icons/` — App icons (32x32, 128x128, 128x128@2x, icon.ico) ✅
- `launcher/tauri_integration.py` — Python adapter script: LauncherService → backend → stdin/stdout JSON ✅
- `launcher/services/tauri_frontend_service.py` — TauriFrontendService implementing FrontendProtocol (no-op) ✅
- `src/frontend/src/services/tauri.ts` — Frontend Tauri IPC helpers (isTauri, getStatus, getHealth, restartBackend, shutdown, showNotification, openUrl, get/setAppConfig) ✅
- `src/frontend/src/services/api.ts` — Updated: detects Tauri context via `window.__TAURI_INTERNALS__`, uses absolute URLs in production ✅
- `docs/TAURI_DESKTOP.md` — Architecture, integration, development, building docs ✅
- Updated `docs/11_Project_Status.md` ✅
- Updated `docs/30-IMPLEMENTATION_PLAN.md` ✅

**Technical Tasks:**
1. Create `desktop/` directory with `package.json` and `@tauri-apps/cli` ✅
2. Create `src-tauri/Cargo.toml` with Tauri v2 and plugin dependencies ✅
3. Configure `tauri.conf.json` with window, build, and bundle settings ✅
4. Configure Tauri to use existing React frontend via `frontendDist` and `devUrl` ✅
5. Write Rust `lib.rs`: plugin init, system tray, window events (close → minimize) ✅
6. Write Rust `commands.rs`: 8 Tauri commands for frontend IPC ✅
7. Write Rust `launcher.rs`: Python child process spawn, stdout read, stdin write, ready detection ✅
8. Write Python `launcher/tauri_integration.py`: LauncherService adapter with JSON protocol ✅
9. Write `tauri_frontend_service.py`: No-op FrontendProtocol for Tauri ✅
10. Generate app icons (32x32, 128x128, ICO) ✅
11. Create `tauri.ts` frontend helper module ✅
12. Update `api.ts` for Tauri context detection ✅
13. Update documentation ✅

**Tests:**
- Launcher starts backend → Python stdout reports "ready" ✅
- Rust reads stdout and detects ready state ✅
- Tauri commands route through stdin/stdout protocol ✅
- Frontend detects Tauri context via `window.__TAURI_INTERNALS__` ✅
- Frontend uses absolute backend URL in Tauri production mode ✅
- System tray created with all 7 menu items ✅
- Window close → minimize to tray ✅
- Tray Exit → shutdown launcher + exit app ✅
- All existing 79 launcher tests still pass ✅

**Acceptance Criteria:**
- Tauri project builds and produces `Eve.exe` ✅
- Tauri configured to use existing React frontend (no second frontend) ✅
- Window resizable, dark theme, min size 800x600 ✅
- System tray with native menu (Open, DevTools, Health, Restart, Settings, Logs, Exit) ✅
- Close window minimizes to tray ✅
- Python launcher starts backend as child process ✅
- Backend health detected via HTTP ✅
- Native notifications via Tauri plugin ✅
- Native clipboard via Tauri plugin ✅
- Native dialogs (open, save, message) via Tauri plugin ✅
- Window state persisted via `tauri-plugin-window-state` ✅
- Packaging configured for MSI/NSIS installer ✅
- No backend APIs modified ✅
- No React frontend redesigned ✅
- Launcher not replaced — Tauri calls LauncherService ✅
- All existing tests pass ✅

**Key Design Decisions:**
- Tauri v2 with plugin architecture (not v1)
- Python launcher runs as child process, not sidecar — simpler setup
- Communication via stdin/stdout JSON lines — no extra ports or sockets
- Existing frontend used as-is with `frontendDist` pointing to `src/frontend/dist`
- Frontend API prefix changes from relative to absolute URL when in Tauri context
- `TauriFrontendService` is a no-op — Tauri manages the webview natively
- Rust commands wrap Python stdin/stdout protocol for frontend IPC
- Window state persisted automatically by plugin (position + size)
- System tray replaces pystray — no Python tray dependency needed

**Estimated Effort:** 2 days

**Completed:** 2026-07-22 — 15 new files, 3 modified files, full integration documented

---

### Sprint 22: AIOS v1.0 Release

**Objective:** Final integration, testing, and release

**Scope:** End-to-end testing, performance testing, documentation review, release

**Dependencies:** All previous sprints

**Deliverables:**
- AIOS v1.0 release
- Integration test suite passing
- Performance benchmarks
- Documentation complete
- Installation package

**Technical Tasks:**
1. Run full E2E test suite
2. Run performance benchmarks
3. Review all documentation
4. Create installation package (Tauri build)
5. Create release notes
6. Tag v1.0.0 release

**Acceptance Criteria:**
- All tests pass
- Performance targets met
- Documentation complete
- Installation package works
- Release tagged

**Risks:**
- Integration issues may surface

**Estimated Effort:** 3 days

---

## 4. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| API key dependency for AI providers | High | Medium | Ollama fallback for local-only development |
| Tesseract installation complexity | Medium | Low | Provide setup script, clear docs |
| Playwright browser dependency | Medium | Low | Auto-install in setup |
| Microphone permission issues | Medium | Low | Handle gracefully, show instructions |
| Window title parsing unreliability | Medium | Low | Multiple fallback strategies |
| SSE reconnection in chat UI | Medium | Low | Implement automatic reconnection |
| Plugin sandbox security | Low | High | Thorough testing, limited permissions |
| Windows API changes | Low | Medium | Abstracted adapter layer |

---

## 5. Definition of Done Checklist

Every module must satisfy all of the following before it is considered complete:

- [ ] Documentation updated
- [ ] Unit tests pass (>90% coverage)
- [ ] Integration tests pass
- [ ] Logging implemented
- [ ] Error handling complete
- [ ] Configuration supported
- [ ] Public interfaces documented
- [ ] No hardcoded values
- [ ] Code review passed
- [ ] Demo verified
