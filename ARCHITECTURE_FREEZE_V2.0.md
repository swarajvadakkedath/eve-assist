# EVE v2.0 — Architecture Freeze

**Date:** August 2026
**Status:** PERMANENTLY FROZEN
**Version:** v2.0-alpha
**Tests:** 464/464 passing

---

This document is the constitutional architecture of EVE. Every future feature must comply with it. The kernel may only be modified for security issues, critical performance issues, or fundamental design flaws. All other work extends, never redesigns, the kernel.

---

## Section 1 — Product Vision

### What EVE Is

EVE is an AI Operating System. Not an AI chatbot. Not an AI assistant. An operating system.

An operating system manages hardware, provides abstractions, and gives applications a uniform interface to the machine. EVE does the same for AI: it manages providers (the "hardware"), provides abstractions (Context Engine, Smart Router, Memory), and gives AI agents a uniform interface to the user's computer.

### The Division

**Hermes provides cognition.** Hermes is the reasoning engine. It plans, thinks, delegates, and executes. It is the "brain."

**EVE provides the operating system.** EVE manages providers, routes requests, handles voice, controls the desktop, remembers everything, recovers from errors, and presents a unified identity. It is the "body."

Neither is complete without the other. Hermes without EVE is a brain without a body. EVE without Hermes is a body without a brain.

### Product Philosophy

1. **The AI is invisible.** The user never sees "Hermes." They see "EVE." Every error, every notification, every response is attributed to EVE. Hermes is an implementation detail.

2. **Free by default.** EVE routes through free providers first. Users opt into paid providers explicitly. This is not a pricing strategy — it is a philosophy: AI should be accessible.

3. **Capability-driven routing.** The Smart Router selects providers based on what the task requires (vision, reasoning, tools, speed), not on model names. The user says "look at this screenshot" — EVE routes to a vision model. The user says "think carefully" — EVE routes to a reasoning model.

4. **Recovery is automatic.** When a provider fails, EVE retries, switches providers, and recovers without user intervention. Errors are intelligence, not failures.

5. **Memory is lifetime.** EVE remembers everything across sessions, projects, and years. Memory is not a feature — it is the foundation of a personal AI.

### Long-Term Direction

EVE evolves from an AI chat interface into a fully autonomous desktop AI that:

- Proactively suggests actions based on context
- Manages files, code, and projects autonomously
- Provides ambient intelligence (not just reactive)
- Operates primarily through voice
- Maintains a lifelong knowledge graph
- Supports a marketplace of skills and agents

Each phase builds on the frozen kernel. The kernel never changes.

---

## Section 2 — System Ownership

Ownership is frozen. Each subsystem owns exactly one domain. No overlap. No duplication.

### Hermes Owns

| Domain | Description |
|--------|-------------|
| Reasoning | Multi-step reasoning, chain-of-thought, reflection |
| Planning | Task decomposition, step sequencing, dependency resolution |
| Skills | Skill loading, execution, composition |
| MCP | Model Context Protocol integration |
| Browser Automation | Web browsing, page interaction, data extraction |
| Subagents | Spawning and managing child agent processes |
| Working Memory | Short-term, session-scoped working memory |

### EVE Owns

| Domain | Description |
|--------|-------------|
| Voice | VoiceSession, STT, TTS, personality, wake word (future) |
| Desktop | Window management, hotkeys, notifications, tray |
| Smart Router | Provider selection, capability matching, fallback |
| AI Operations Center | Dashboard, monitoring, diagnostics, recovery UI |
| AI Error Intelligence | Error classification, recovery strategies, timeline |
| Context Engine | Environmental awareness, provider aggregation |
| Life Memory | Long-term knowledge graph, project memory, session memory |
| Security | Authentication, permissions, sandboxing, credential handling |
| Windows Integration | Process management, clipboard, file system |
| Tool Execution | ToolManager, tool registration, tool lifecycle |
| Provider Routing | Multi-provider, multi-model, commercial policy |
| Identity | EVE persona, Hermes sanitization, user-facing attribution |
| Recovery | Automatic retry, provider switching, error recovery |

### Boundary Rule

No module may cross ownership boundaries. If Hermes needs desktop information, it receives it through ExecutionContext — it never calls Windows APIs directly. If EVE needs reasoning, it sends a request through the agent adapter — it never invokes Hermes internals.

---

## Section 3 — Complete Architecture Diagram

```
+-----------------------------------------------------------+
|                        USER                               |
|              Voice / Chat / Overlay / CLI                 |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|               CONVERSATION PIPELINE                       |
|  Validate | Identity | Context | Intent | Delegate |     |
|  Manager | Post-process | Output                          |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                    IDENTITY LAYER                         |
|         Persona | Hermes Sanitization | Attribution       |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                  CONTEXT ENGINE                           |
|  Clipboard | Window | Workspace | Git | Browser |         |
|  Memory | Calendar | Selection | Application | Tool |     |
|  Notification | Desktop | ProviderHealth | Voice          |
|                                                           |
|  -> ExecutionContext (14 sub-contexts, versioned)         |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|               HERMES AGENT ENGINE                         |
|       Reasoning | Planning | Skills | Subagents           |
|                                                           |
|  Receives: ExecutionContext, user objective               |
|  Returns: AgentResult with tool_calls, output             |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                 MEMORY MEDIATOR                           |
|       Session | Project | Global scopes                   |
|       Attribution: always "EVE"                            |
|       Hermes never accesses persistence directly          |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                  TOOL MEDIATOR                            |
|       Permission checks | Audit logging                   |
|       Identity sanitization | Error intelligence          |
|       ToolManager -> Desktop Services -> Windows          |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                   SMART ROUTER                            |
|       Capability matching | Health-aware routing          |
|       Commercial policy | Fallback hierarchy              |
|       Priority weighting | Latency optimization           |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|                 PROVIDER MANAGER                          |
|       17 providers | Model discovery                      |
|       Background refresh | Health monitoring              |
|       Credential pools | Commercial policy                |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|          PROVIDERS (OpenAI, Google, Groq, ...)            |
|       OpenAI-compatible adapters | Native adapters        |
|       Model catalogs | Capability inference               |
+---------------------------+-------------------------------+
                            |
                            v
+-----------------------------------------------------------+
|            DESKTOP / BROWSER / FILES                      |
|       Windows API | Clipboard | Process | File system     |
|       Browser engine | Vision | Voice hardware            |
+-----------------------------------------------------------+
```

---

## Section 4 — Execution Pipeline

Every request follows this pipeline. No shortcuts. No bypasses.

### Non-Streaming (send_message)

```
1. Validate      - Strip whitespace, check empty
2. Identity      - Set EVE persona, strip Hermes patterns
3. Context       - Snapshot from 14 providers via Context Engine
4. Intent        - Classify user intent (question, tool, conversation)
5. Delegate      - Route through Pipeline hooks (pre-processing)
6. Manager       - Build messages, query LLM, handle tool calls
   6a. Memory    - Retrieve relevant memories via MemoryMediator
   6b. Tools     - Get available tools (sanitized)
   6c. LLM       - Send to Smart Router -> Provider
   6d. Tool Loop - If LLM returns tool_calls:
       - Execute each through ToolMediator
       - Append tool results
       - Re-query LLM
       - Repeat until no tool_calls (max 10 iterations)
7. Post-process  - Sanitize Hermes patterns from response
8. Output        - Return response to user
```

### Streaming (stream_message)

```
1-5. Same as non-streaming
6. Manager       - Build messages, stream from Smart Router
   6a-6b. Same as non-streaming
   6c. Stream    - Token-by-token pass-through to client
       (Tool calling not yet supported in streaming mode)
7. Post-process  - Sanitize response
8. Output        - Yield events to client
```

### Agent Path (EveAgentAdapter)

```
1. AgentTurnRequest received
2. Build ChatRequest (resolve capability aliases)
3. Route through Smart Router (category, policy, commercial)
4. Provider executes inference
5. Return AgentResult (content, tool_calls, trace)
6. Tool execution goes through ToolMediator (never direct)
```

### Pipeline Invariants

- Every request goes through the pipeline
- Identity Layer runs on every request (ingress and egress)
- Context Engine provides fresh context on every request
- Tool execution always goes through ToolMediator
- Memory access always goes through MemoryMediator
- Provider selection always goes through Smart Router
- Errors always go through Error Intelligence

---

## Section 5 — Context Architecture

### Context Engine

The Context Engine is the kernel of environmental awareness. It aggregates context from 14 providers into a single ExecutionContext snapshot.

**Location:** `aios/core/context/engine.py`

### ExecutionContext

A versioned, immutable snapshot of the user's environment. Contains 14 sub-contexts:

| Sub-Context | Provider | Data |
|-------------|----------|------|
| WindowContext | WindowProvider | Active app, window, file, activity |
| ClipboardContext | ClipboardProvider | Clipboard text (truncated 10KB) |
| WorkspaceContext | WorkspaceProvider | Recent files, workspace path, project info |
| GitContext | GitProvider | Branch, dirty status, remote URL |
| BrowserContext | BrowserProvider | Active tab, URL, open tabs |
| DesktopContext | DesktopProvider | Status, hotkey count |
| VoiceContext | VoiceProvider | Session state, active, listening |
| MemoryContext | MemoryProvider | Total memories, recent count |
| ProviderHealthContext | ProviderHealthProvider | Per-provider health, overall status |
| CalendarContext | CalendarProvider | Events, next meeting |
| SelectionContext | SelectionProvider | Selected text, source |
| ApplicationContext | ApplicationProvider | Running processes |
| ToolContext | ToolProvider | Available tools, recent calls |
| NotificationContext | NotificationProvider | Pending, recent, unread |

### Providers

Each provider is modular, testable, and knows nothing about Hermes. Providers collect structured data from a single source and return a dict.

**All providers are async.** No blocking subprocess calls allowed. ClipboardProvider and GitProvider use `asyncio.create_subprocess_exec()`.

### Caching

- ClipboardProvider: 2-second TTL
- GitProvider: 10-second TTL
- Section cache: 30-second TTL
- Provider-level caching via `_section_cache`

### Versioning

Every ExecutionContext has a monotonically increasing version number. Consumers can detect changes by comparing versions.

### Privacy

Providers declare a ContextScope (PUBLIC or PRIVATE). Private context (clipboard, voice, memory) is never exposed to external systems. The context engine respects scope boundaries.

### Incremental Updates

`ContextEngine.collect()` computes a diff against the previous snapshot. Only changed sections trigger events and notifications.

---

## Section 6 — Memory Architecture

### Working Memory (Session)

- **Scope:** Single conversation session
- **Storage:** In-memory dictionary on ConversationManager
- **Lifetime:** Until conversation ends
- **Access:** MemoryMediator.recall() with scope="session"

### Life Memory (Long-term)

- **Scope:** Global, Project, or Session
- **Storage:** Graph store (MemorySystem -> MemoryStore -> MemoryGraph)
- **Lifetime:** Persistent across restarts
- **Access:** MemoryMediator.recall() or MemoryMediator.store()

### MemoryMediator

The sole interface between conversations and memory. Enforces:

1. **Scope enforcement** — Session scope does not query graph store
2. **Attribution** — All memories attributed to "EVE" (never "Hermes")
3. **Isolation** — Hermes never accesses persistence directly

**Location:** `aios/mediation/memory.py`

### Scopes

| Scope | Storage | Queryable | Persistent |
|-------|---------|-----------|------------|
| SESSION | In-memory dict | Only within session | No |
| PROJECT | Graph store | By project ID | Yes |
| GLOBAL | Graph store | Globally | Yes |

### Persistence

Graph store persists to disk via JSON files. Memory is loaded on startup and saved on mutation.

---

## Section 7 — Tool Architecture

### The Mediation Chain

```
Hermes (or LLM tool_call)
    |
    v
ToolMediator.execute()
    |
    v
Permission checks (PermissionManager)
    |
    v
Audit logging (1000-entry ring buffer)
    |
    v
Identity sanitization (Hermes -> EVE)
    |
    v
Error intelligence capture
    |
    v
ToolManager.execute()
    |
    v
Desktop Services (WindowsAdapter, BrowserEngine, etc.)
    |
    v
Windows / Browser / File System
    |
    v
Result returned through same chain
```

### Why Direct Execution Is Forbidden

1. **No permission enforcement.** Without the mediator, any tool can be executed without permission checks.
2. **No audit trail.** Without the mediator, tool executions are invisible to the system.
3. **No identity sanitization.** Tool descriptions might contain Hermes references.
4. **No error intelligence.** Tool failures are not captured, classified, or recovered.
5. **No timeout enforcement.** Tools could hang indefinitely.
6. **No event publishing.** Tool executions don't appear in the AI Operations Center.

### Tool Registration

Tools are registered in categories:
- builtin, system, content, developer, devtools, git, network, office, productivity, browser

Each tool has: id, name, description, category, parameters (JSON Schema), permission_level (0=auto, 1=ask, 2=deny).

---

## Section 8 — Voice Architecture

### VoiceSession Manager

Manages the lifecycle of a voice interaction:

```
IDLE -> LISTENING -> PROCESSING -> SPEAKING -> IDLE
```

**Location:** `aios/voice/session.py`

### Components

| Component | Role |
|-----------|------|
| STT | Speech-to-text (local or cloud) |
| TTS | Text-to-speech (pyttsx3 default) |
| VoicePersonalityManager | Format responses for speech |
| VoiceProvider | Context Engine integration |
| EventBus | State change notifications |

### VoicePersonalityManager

Formats LLM responses for spoken delivery:
- Removes markdown formatting
- Expands abbreviations (20 patterns)
- Context-aware tone selection (8 tone profiles)
- Sentence restructuring for natural speech

**Location:** `aios/personality/voice.py`

### Future Capabilities

- Wake-word detection (Picovoice or similar)
- Continuous conversation mode
- Voice Activity Detection (VAD)
- Word-level TTS streaming
- Multi-turn voice context
- Voice becomes the primary interface

---

## Section 9 — Identity

### Identity Layer

The Identity Layer ensures EVE is always EVE. It operates on every request (ingress) and every response (egress).

**Location:** `aios/identity/layer.py`

### Four Sanitization Layers

| Layer | Location | What It Sanitizes |
|-------|----------|-------------------|
| Identity Layer | `identity/layer.py` | Error messages, system prompts |
| Pipeline | `pipeline.py` | Responses (hermes -> EVE pattern replacement) |
| Events Bridge | `hermes_bridge/events.py` | Recursive dict sanitization on EventBus |
| Tool Mediation | `mediation/tools.py` | Tool descriptions and names |

### Persona

EVE's persona is defined in the system prompt. It is:
- Professional but warm
- Helpful without being subservient
- Technically capable
- Always attributed as "EVE"

### Prompt Ownership

The system prompt is owned by the ConversationPipeline. It is built from:
- Base persona (EVE identity)
- Context (from ExecutionContext)
- Memory (from MemoryMediator)
- Tools (sanitized by ToolMediator)

### Voice Ownership

Voice responses are formatted by VoicePersonalityManager before TTS. The personality layer ensures spoken responses match EVE's persona.

### Notification Ownership

All notifications, errors, and user-facing messages are attributed to "EVE." Hermes never appears in:
- Error messages
- Notification text
- UI labels
- Log messages visible to users

### Hermes Must Never Become Visible

This is the most important identity rule. The user interacts with EVE. Hermes is an implementation detail that powers EVE's reasoning but is never exposed.

---

## Section 10 — Recovery

### AI Error Intelligence

**Location:** `aios/error_intelligence/`

Captures, classifies, and tracks all errors:
- 21 error categories (PROVIDER, ROUTING, NETWORK, VOICE, etc.)
- 5 severity levels (INFO, LOW, MEDIUM, HIGH, CRITICAL)
- Bounded ring buffer (1000 events)
- JSON persistence (~/.eve/errors.json)
- Timeline tracking
- Recovery attempt logging

### Recovery Engine

**Location:** `aios/error_intelligence/recovery_engine.py`

Stateless engine with injected dependencies. Strategies:

| Strategy | Behavior |
|----------|----------|
| NONE | No recovery |
| RETRY | Re-route via Smart Router |
| SWITCH_PROVIDER | Exclude failed provider, re-route |
| REFRESH_MODELS | Invalidate cache, re-route |
| COOLDOWN | Record 429, wait, re-route |
| RETRY_OR_SWITCH | Try retry first, switch on failure |
| SUGGEST_ONLY | Return suggestions, no action |

### Autonomous Recovery

Recovery is triggered automatically:
- Stream errors: classified and captured
- Manager errors: `_capture_error()` triggers `attempt_recovery()` (fire-and-forget)
- Tool errors: captured by ToolMediator
- Three recovery levels: retry same provider, switch provider, refresh models

---

## Section 11 — Observability

### AI Operations Center

**Location:** `src/frontend/src/components/aio/`

8-tab dashboard:

| Tab | Data Source | Polling |
|-----|-------------|---------|
| Dashboard | All sources | On load |
| Providers | ProviderManager | 30s |
| Models | Model catalog | 60s |
| SmartRouter | Routing config | On load |
| Health | HealthMonitor | 10s |
| Recovery | ErrorIntelligence | 30s |
| Activity | EventBus | Real-time |
| Settings | AiosSettings | On load |

### Runtime Metrics

- Provider health scores (success rate + latency)
- Error recovery rates
- Context poll latency
- Memory store/recall counts
- Tool execution counts and durations
- Voice session metrics

### Event System

EventBus publishes:
- `context:*` — Context changes
- `health:*` — Provider health changes
- `error:*` — Error captured
- `tool:*` — Tool execution events
- `memory:*` — Memory operations
- `voice:*` — Voice state changes
- `agent:*` — Agent events

### Diagnostics

Available via `GET /api/v1/providers/diagnostics`:
- Version info
- Provider count and status
- Context engine version
- Memory store stats
- Error intelligence stats
- Recovery attempt counts

---

## Section 12 — Security

### Authentication

- Bearer token auth on all API endpoints
- Token generated on startup: `secrets.token_urlsafe(32)`
- Token prefix (4 chars) logged for debugging
- `/auth/token` endpoint: localhost-only, no auth (desktop bootstrap)
- Frontend fetches token from `/auth/token`, attaches as Bearer header

### Permissions

- PermissionManager controls tool execution permissions
- Three levels: 0=auto, 1=ask, 2=deny
- Per-tool permission configuration
- Plugin permissions scoped to plugin

### Sandboxing

- Subprocess execution uses `asyncio.create_subprocess_exec()` (no shell=True)
- Timeouts on all subprocess calls (5s default)
- No arbitrary code execution from user input

### Memory Isolation

- Session memory is ephemeral (in-memory only)
- Project memory scoped by project ID
- Global memory accessible across projects
- Hermes never accesses memory directly

### Tool Permissions

- ToolMediator enforces permission checks before execution
- Audit log records every tool call (1000-entry ring)
- Tool descriptions sanitized (Hermes references removed)

### Context Privacy

- Private context (clipboard, voice, memory) not exposed externally
- ContextScope enum: PUBLIC | PRIVATE
- Password manager detection suppresses context collection

### Credential Handling

- API keys stored in memory only (never logged)
- `sanitize_error()` redacts API keys, tokens, passwords from error strings
- Provider adapters store keys in `_headers` (not in logs)
- Routing diagnostics strip credential fields

---

## Section 13 — Extension Points

Future modules may extend the architecture. They may never replace it.

### Voice Extensions

- Custom TTS engines (replace pyttsx3)
- Custom STT engines (replace default)
- Wake-word detectors
- Voice Activity Detection
- Multi-language support

### Desktop Widgets

- Tauri multi-window support
- System tray extensions
- Notification enhancements
- Global hotkey extensions
- File system watchers

### Agent Runtimes

- New AgentRuntime implementations
- Custom reasoning strategies
- Domain-specific agents
- Multi-agent orchestration

### Memory Providers

- Vector database backends
- Semantic search providers
- Knowledge graph extensions
- External memory sources

### Context Providers

- New context sources (calendar, email, etc.)
- Custom project detection
- Activity classification extensions
- Custom scope types

### Tools

- New tool categories
- Custom tool implementations
- Tool composition (meta-tools)
- Remote tool execution

### Themes

- UI theme system
- Voice personality profiles
- Color schemes
- Accessibility themes

### Plugins

- Plugin marketplace
- Skill registry
- Community contributions
- Enterprise extensions

---

## Section 14 — Architectural Rules

These rules are immutable. They may only be changed by the architecture freeze process.

### Identity Rules

1. Hermes must never become visible to the user
2. All user-facing attribution is "EVE"
3. Identity Layer runs on every request
4. Four sanitization layers must all be maintained
5. Error messages are sanitized before display

### Execution Rules

6. Every request goes through the Conversation Pipeline
7. Tool execution always goes through ToolMediator
8. Memory access always goes through MemoryMediator
9. Provider selection always goes through Smart Router
10. No direct access to providers from agents

### Context Rules

11. Context always comes through ExecutionContext
12. All providers are async (no blocking calls)
13. Private context is never exposed externally
14. Context Engine owns all provider lifecycle
15. Incremental updates via diff computation

### Memory Rules

16. Hermes never accesses memory persistence directly
17. All memory attribution is "EVE"
18. Session scope is ephemeral
19. Project scope is isolated by project ID
20. Global scope is shared across projects

### Tool Rules

21. ToolMediator is mandatory for all tool execution
22. Permission checks happen before execution
23. Every tool call is audit-logged
24. Tool descriptions are sanitized
25. Tool errors go through Error Intelligence

### Router Rules

26. Smart Router selects all providers
27. Capability matching drives selection
28. Health state influences routing
29. Commercial policy is enforced
30. Fallback hierarchy is: free -> free_tier -> credit -> local -> paid

### Security Rules

31. All API endpoints require auth (except documented exceptions)
32. Subprocess calls never use shell=True
33. Credentials are never logged
34. Error strings are sanitized
35. Memory isolation is enforced

---

## Section 15 — Future Roadmap

Each phase builds on the frozen kernel. The kernel never changes.

### Phase D — VoiceOS+

Voice becomes the primary interface.

- Wake-word detection
- Continuous conversation mode
- Voice Activity Detection
- Word-level TTS streaming
- Multi-turn voice context
- Voice personality expansion
- Overlay voice indicator

**Depends on:** Frozen kernel (Phase C complete)
**Extends:** VoiceSession, VoicePersonalityManager, VoiceProvider

### Phase E — Autonomous Desktop

EVE proactively manages the desktop.

- File system monitoring and organization
- Code repository management
- Automated git workflows
- Desktop widget system (Tauri multi-window)
- System tray with proactive suggestions
- Notification intelligence

**Depends on:** Phase D (voice-driven desktop commands)
**Extends:** DesktopProvider, WindowsAdapter, WorkspaceManager

### Phase F — Ambient Intelligence

EVE provides context-aware proactive assistance.

- Activity prediction
- Intent inference from context
- Proactive suggestions
- Workflow automation
- Meeting intelligence
- Code review automation
- Smart scheduling

**Depends on:** Phase E (desktop awareness)
**Extends:** ContextEngine, MemorySystem, ConversationPipeline

### Phase G — Life Memory

EVE maintains a lifelong knowledge graph.

- Semantic search across all memories
- Knowledge graph visualization
- Relationship mapping
- Cross-project insights
- Personal knowledge management
- Memory consolidation
- Forgetting and relevance decay

**Depends on:** Phase F (ambient data collection)
**Extends:** MemorySystem, MemoryMediator, MemoryProvider

### Phase H — Agent Marketplace

EVE supports a marketplace of skills and agents.

- Skill registry and discovery
- Agent runtime marketplace
- Community contributions
- Enterprise extensions
- Version management
- Dependency resolution
- Rating and review system

**Depends on:** Phase G (memory for skill learning)
**Extends:** PluginManager, SkillRegistry, AgentRuntime

---

## Section 16 — Change Control

From this point forward, core architecture may only change if:

1. **Security issue** — A vulnerability is discovered that requires architectural change
2. **Critical performance issue** — A bottleneck is found that cannot be solved by extension
3. **Fundamental design flaw** — A logical error in the architecture is discovered

All other future work **extends, never redesigns** the kernel.

### Extension Process

1. New module proposes an extension point
2. Extension must use existing interfaces (ContextProvider, AgentRuntime, Tool, etc.)
3. Extension must not modify core modules
4. Extension must pass all existing tests
5. Extension must add its own tests
6. Extension is reviewed against Architectural Rules

### Deprecation Process

1. Core module is marked as deprecated
2. Extension point is provided as replacement
3. Migration guide is written
4. Old module is maintained for 2 major versions
5. Old module is removed

### Version Control

- Architecture version: v2.0
- Kernel version: v2.0-alpha
- Extension points are versioned independently
- Breaking changes require architecture version bump

---

**END OF ARCHITECTURE FREEZE**

This document is the single source of truth for EVE's architecture.

Phase C is permanently frozen.

Development moves exclusively to Phase D — VoiceOS+.
