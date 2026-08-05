# EVE v2.0 — Context Engine (AI Operating System Kernel)

## Architecture

```
                    Windows
                        │
 ┌──────────────────────┼─────────────────────────┐
 │                      │                         │
Clipboard         Workspace                 Browser
Git               Calendar                 Voice
Desktop           Selection                Running Apps
Memory            Provider Health          AI Operations
 │                      │                         │
 └──────────────────────┼─────────────────────────┘
                        │
                Context Providers
                        │
                 Context Engine
                        │
               ExecutionContext
                        │
               Hermes Agent Engine
                        │
               EVE Agent Adapter
                        │
                 Smart Router
```

## Core Concept

**ExecutionContext** is the universal context object. Every EVE subsystem and Hermes receives this object. Hermes NEVER accesses OS services directly — everything flows through ExecutionContext.

## Components

### ExecutionContext

The unified context object containing 14 sub-contexts:

| Section | Type | Description |
|---------|------|-------------|
| `window` | `WindowContext` | Active app, window, file, activity |
| `clipboard` | `ClipboardContext` | Clipboard content (private) |
| `workspace` | `WorkspaceContext` | Current project, recent files |
| `git` | `GitContext` | Repository, branch, dirty state |
| `browser` | `BrowserContext` | Active tab, URL, open tabs |
| `desktop` | `DesktopContext` | Tray, notifications, hotkeys |
| `voice` | `VoiceSession` | Listening, speaking, transcript |
| `memory` | `MemoryContext` | Relevant/recent/project memories |
| `provider_health` | `ProviderHealthContext` | Provider states, scores |
| `calendar` | `CalendarContext` | Events, next meeting |
| `selection` | `SelectionContext` | Selected text (private) |
| `application` | `ApplicationContext` | Running processes |
| `tools` | `ToolContext` | Available tools, recent calls |
| `notifications` | `NotificationContext` | Pending notifications |

### Context Providers

14 modular providers, each owning one data source:

- `ClipboardProvider` — clipboard content
- `WindowProvider` — active window via WindowsAdapter
- `WorkspaceProvider` — project and file tracking
- `GitProvider` — git repository state
- `BrowserProvider` — browser tabs (stub)
- `DesktopProvider` — tray, hotkeys, notifications
- `VoiceProvider` — voice session state
- `MemoryProvider` — memory queries
- `ProviderHealthProvider` — AI provider health
- `CalendarProvider` — calendar events (stub)
- `SelectionProvider` — selected text
- `ApplicationProvider` — running processes
- `ToolProvider` — tool availability
- `NotificationProvider` — pending notifications

### Context Engine

The kernel that orchestrates everything:

- **Provider Registration**: `register_provider()` / `unregister_provider()`
- **Context Collection**: `collect()` — gathers from all providers concurrently
- **Context Access**: `snapshot()` — returns current context
- **Incremental Updates**: `diff()` — only changed sections refresh
- **Versioning**: Every snapshot has version number + changed_providers
- **Caching**: Section-level cache with TTL
- **Subscriptions**: `subscribe(callback)` — notified on changes
- **Event Integration**: Subscribes to EventBus events
- **Diagnostics**: `diagnostics()` for AI Operations Center

### Context Policy

Privacy enforcement before context exposure:

- Sensitive clipboard detection (API keys, tokens, passwords)
- Password manager detection (1Password, Bitwarden, etc.)
- Incognito browser detection
- Sensitive path filtering (.ssh, .env, credentials)
- App blocking (configurable blocklist)

## Data Flow

```
User message
  → Voice / Chat / Overlay
    → ConversationManager
      → ContextEngine.snapshot()
        → ExecutionContext (all 14 sections)
      → ContextPolicy.enforce()
        → Redacted ExecutionContext
      → Hermes Agent Engine
        → NEVER accesses OS directly
      → Tool Mediation
      → Smart Router
      → Provider
      → Response
```

## Incremental Updates

Context Engine tracks changes between snapshots:

1. Provider collects data
2. Engine builds ExecutionContext
3. `diff()` compares with previous snapshot
4. Only changed sections trigger events
5. Cache invalidated only for changed sections
6. Subscribers notified with change list

## Versioning

Every ExecutionContext has:
- `context_id`: Unique identifier
- `version`: Monotonically increasing integer
- `timestamp`: UTC timestamp
- `changed_providers`: List of sections that changed

Consumers can check `version` to know if context is stale.

## Caching

Section-level cache with configurable TTL:
- `get_section_cache(section)` — returns cached data if valid
- `invalidate_cache(section)` — force refresh
- Cache populated on each `collect()` call

## Event Integration

Context Engine publishes events to EventBus:
- `context:changed` — any context change
- `context:window_changed` — window section changed
- `context:clipboard_changed` — clipboard changed
- `context:workspace_changed` — workspace changed
- `context:git_changed` — git state changed
- `context:voice_changed` — voice state changed
- `context:memory_changed` — memory updated
- `context:provider_health_changed` — provider health changed

## Privacy Model

Context sections have privacy scopes:
- `PUBLIC` — always exposed (desktop, git, application)
- `PRIVATE` — exposed with awareness (clipboard, browser, selection, voice)
- `SENSITIVE` — filtered by policy (password managers, API keys)
- `RESTRICTED` — blocked entirely (configurable blocklist)

ContextPolicy enforces filtering before context reaches Hermes.

## Performance Targets

| Operation | Target | Actual |
|-----------|--------|--------|
| Context build | <100ms | ~5ms |
| Context update | <20ms | ~1ms |
| Diff computation | <1ms | <0.1ms |
| Hash computation | <5ms | <1ms |

## AI Operations Center Integration

Exposed via `/api/v1/context/*`:
- `GET /diagnostics` — engine version, provider count, cache stats
- `GET /snapshot` — current ExecutionContext
- `GET /providers` — registered providers
- `GET /version` — current version
- `POST /refresh` — force refresh
- `GET /policy/evaluate` — privacy evaluation

## Backward Compatibility

- `Context` alias → `ExecutionContext`
- `get_active_app()` / `get_active_file()` / `detect_project()` — legacy API preserved
- Old `ContextEngine` constructor signature preserved
- `core/context_engine.py` re-export shim updated

## Files

- `core/context/models.py` — ExecutionContext, all sub-contexts, ContextProvider base
- `core/context/engine.py` — ContextEngine (the kernel)
- `core/context/policy.py` — ContextPolicy (privacy enforcement)
- `core/context/providers/base.py` — 14 context providers
- `api/context_api.py` — AI Operations Center endpoints
- `tests/phase_b/test_context_engine.py` — 40 comprehensive tests
