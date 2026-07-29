# 09 — Architecture Decision Record Log

> **Status:** Active · v2.1.0  
> **Scope:** Complete architectural history of Eve OS (AIOS)  
> **Last Updated:** 2026-07-21  
> **ADR Count:** 16 (8 Adopted · 1 Proposed · 7 Draft)  
> **Maintainer:** Engineering Lead

---

## Table of Contents

1. [ADR Process](#1-adr-process)
2. [ADR Index](#2-adr-index)
3. [Active ADRs](#3-active-adrs)
4. [Appendix A — ADR Template](#4-appendix-a--adr-template)
5. [Appendix B — Decision Theme Index](#5-appendix-b--decision-theme-index)
6. [Appendix C — Superseded ADRs](#6-appendix-c--superseded-adrs)

---

## 1. ADR Process

### 1.1 When to Write an ADR

An ADR is required when a decision:

- Changes the public API of a module
- Introduces a new dependency or technology
- Alters the communication flow between modules
- Changes the data model or persistence strategy
- Adds, removes, or modifies a security boundary
- Changes the build, packaging, or distribution pipeline
- Has cross-module impact (affects 2+ modules)
- Introduces a new architectural pattern

### 1.2 ADR Lifecycle

```
                         ┌─────────────┐
                         │   Draft     │
                         └──────┬──────┘
                                │
                                ▼
                         ┌─────────────┐
                    ┌────│  Proposed   │────┐
                    │    └─────────────┘    │
                    │                       │
                    ▼                       ▼
             ┌──────────┐          ┌──────────────┐
             │ Adopted   │          │  Rejected    │
             └─────┬─────┘          └──────────────┘
                   │
           ┌───────┴────────┐
           ▼                 ▼
    ┌──────────┐     ┌──────────────┐
    │ Active   │     │ Superseded   │
    └──────────┘     └──────────────┘
                         │
                         ▼
                  ┌──────────────┐
                  │  Deprecated  │
                  └──────────────┘
```

| Status | Meaning |
|--------|---------|
| **Draft** | Being written, not yet reviewed |
| **Proposed** | Under review, not yet implemented |
| **Adopted** | Approved and implemented |
| **Active** | Currently in effect |
| **Superseded** | Replaced by a newer ADR (reference included) |
| **Deprecated** | No longer recommended, but still in use |
| **Rejected** | Considered and declined |

### 1.3 ADR Numbering

- ADRs are numbered sequentially: `ADR-0001`, `ADR-0002`, ...
- Numbers are never reused (even for superseded ADRs)
- Superseding ADRs reference the ADRs they replace

### 1.4 Where ADRs Live

- **Active ADRs:** `docs/adr/ADR-NNN-title.md` (individual files)
- **ADR Log:** `docs/09_ADR_Log.md` (this file — master index and full content)
- **Proposed ADRs:** `docs/adr/proposals/ADR-NNN-title.md`

---

## 2. ADR Index

| # | Title | Status | Date | Theme | Page |
|---|-------|--------|------|-------|------|
| 0001 | Desktop Shell — Tauri + Python Sidecar | **Adopted** · Active | 2026-05-01 | Desktop Packaging | 3 |
| 0002 | Event Bus — In-Process Async Message Bus | **Adopted** · Active | 2026-05-05 | Infrastructure | 5 |
| 0003 | AI Router — Multi-Provider Strategy with Fallback | **Adopted** · Active | 2026-05-10 | Intelligence | 7 |
| 0004 | Capability Registry — Planner-Tool Decoupling | **Adopted** · Active | 2026-05-15 | Architecture | 9 |
| 0005 | Permission System — Four-Tier Progressive Model | **Adopted** · Active | 2026-05-20 | Security | 11 |
| 0006 | Persistence — SQLite with Vector Extensions | **Adopted** · Active | 2026-05-25 | Persistence | 13 |
| 0007 | Memory Architecture — Temporal Knowledge Graph | **Proposed** | 2026-06-01 | Memory | 15 |
| 0008 | Memory Core — Zero-Dependency Graph Subsystem | **Adopted** · Active | 2026-06-10 | Memory Core | 17 |
| 0009 | Frontend Architecture — State-Driven Workspace Registry | **Adopted** · Active | 2026-06-15 | Frontend Architecture | 19 |
| 0010 | Design System — CSS Custom Property Tokens | **Adopted** · Active | 2026-06-20 | Design System | 21 |
| 0011 | Execution Engine — Deterministic State Machine | **Adopted** · Active | 2026-06-25 | Execution | 23 |
| 0012 | Command Center — Keyboard-First Universal Palette | **Adopted** · Active | 2026-07-01 | Command Center | 25 |
| 0013 | Activity Center — Event-Backed Notification Feed | **Adopted** · Active | 2026-07-05 | Activity | 27 |
| 0014 | Inspector — Reactive Session Detail Panel | **Adopted** · Active | 2026-07-10 | Inspector | 29 |
| 0015 | Authentication — Local-First Device Identity | **Draft** | 2026-07-15 | Authentication | 31 |
| 0016 | Capability Registry (Future) — Plugin-Powered Discovery | **Draft** | 2026-07-20 | Future Capability Registry | 33 |

---

## 3. Active ADRs

---

### ADR-0001: Desktop Shell — Tauri + Python Sidecar

**Status:** Adopted · Active  
**Date:** 2026-05-01  
**Author:** Engineering Lead  
**Theme:** Desktop Packaging

#### Decision

Use **Tauri 2.x** as the desktop shell with a **React + TypeScript** frontend and a **Python + FastAPI** backend running as a sidecar process.

- **Shell:** Tauri 2.x (Rust)
- **Frontend:** React 18, TypeScript 5.5, Vite 5
- **Backend:** Python 3.12+, FastAPI, uvicorn
- **Communication:** Localhost HTTP (REST on port 8456)

#### Context

Eve OS is a desktop AI co-pilot for Windows. It requires:
- A native desktop window with system tray integration
- A rich, responsive UI (React)
- Access to the full Python AI/ML ecosystem (LLMs, OCR, speech, automation)
- Small installer size for a consumer desktop application
- Security isolation between UI and system-level operations

The team evaluated six desktop application architectures before selecting Tauri.

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Electron** | ~150MB minimum bundle, performance overhead, memory hunger. 30x larger than Tauri. |
| **Qt/C++** | Steep learning curve, weaker AI/ML ecosystem integration, slower development velocity. |
| **.NET MAUI / WPF** | Windows-only, weaker Python interop, smaller ecosystem for desktop AI tools. |
| **Go backend** | Inferior AI/ML library ecosystem compared to Python. |
| **Java (Swing/JavaFX)** | Poor desktop UX, large runtime dependency, not aligned with AI ecosystem. |
| **Flutter Desktop** | Immature on Windows at time of decision, limited native API access. |

#### Consequences

**Positive:**
- ~5MB installer (excluding Python runtime)
- Rust provides strong security guarantees for the shell layer
- Python sidecar can be updated independently of the shell
- Full access to Python AI/ML ecosystem (OpenAI, Anthropic, Ollama, Tesseract, PyAutoGUI, Playwright, etc.)
- React frontend enables rapid UI iteration
- Localhost HTTP communication is simple, debuggable, and language-agnostic

**Negative:**
- Python runtime must be bundled with the installer (~30-50MB)
- Two-process architecture adds communication latency (~1-2ms per call)
- Rust knowledge required for shell configuration changes
- Tauri's Python sidecar pattern is less documented than Electron or Qt
- Startup time includes both Node/Vite and Python process initialization

**Neutral:**
- Frontend and backend can be developed independently
- Future migration to a different shell is possible without changing backend or frontend

#### Future Impact

- Python bundling strategy must be solved for distribution (embedded Python, PyInstaller, or system Python)
- Tauri 3.x may simplify sidecar management (monitor for breaking changes)
- If Tauri's community support declines, migration path to Electron is feasible (same frontend + backend)
- Cross-platform support (macOS, Linux) is theoretically possible but will require per-OS adapter implementations

#### Related ADRs

- [ADR-0009](#adr-0009-frontend-architecture--state-driven-workspace-registry): Frontend architecture within the Tauri webview
- [ADR-0016](#adr-0016-desktop-packaging--tauri-installer-with-squirrel-updates): Packaging and distribution strategy
- [ADR-0015](#adr-0015-authentication--local-first-device-identity): Security model for the desktop shell

---

### ADR-0002: Event Bus — In-Process Async Message Bus

**Status:** Adopted · Active  
**Date:** 2026-05-05  
**Author:** Engineering Lead  
**Theme:** Infrastructure

#### Decision

Implement an **in-process async event bus** using Python's `asyncio` with:
- Internal `asyncio.Queue` for message delivery
- Subscription dictionary keyed by event type
- Wildcard subscription patterns (`*`, `domain:*`)
- At-least-once delivery semantics
- Retry with exponential backoff (1s, 2s, 4s; max 3 retries)
- Dead letter queue for permanently failed events
- Event history buffer (capped at 10,000 events, trims to 5,000)
- Priority queue for critical system events

#### Context

All modules in Eve OS must communicate without direct imports. The architecture freeze mandates: *"All communication through Event Bus, no direct module imports."* The Event Bus is the central nervous system of the application.

Requirements:
- Zero external dependencies for core functionality
- Async-first to support I/O-bound operations
- At-least-once delivery for critical events (permissions, execution)
- Pattern-based subscriptions (observe all `tool:*` events)
- Event persistence for crash recovery
- Desktop app scale — no need for distributed messaging

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **RabbitMQ** | External service, overkill for a single-desktop-app architecture. Requires Erlang runtime. |
| **Redis Pub/Sub** | External dependency, no persistence by default, adds ~10MB to installer. |
| **gRPC streams** | Too heavy for in-process communication. Adds protobuf compilation step. |
| **ZeroMQ** | Complex socket management, no built-in retry or dead letter queue. |
| **Direct method calls** | Violates architecture freeze. Creates tight coupling between modules. |

#### Consequences

**Positive:**
- Zero external dependencies for core functionality
- Async dispatch prevents blocking the publisher
- At-least-once delivery with retry ensures reliability for critical events
- Dead letter queue provides observability for failed events
- Event history enables replay and recovery
- Wildcard subscriptions give flexibility for monitoring and logging

**Negative:**
- Single point of failure — if the bus crashes, inter-module communication stops
- In-process only — cannot be used for inter-process or distributed communication
- Event history in memory (not persisted) — lost on restart
- No built-in event schema validation — must be implemented by consumers
- Async queue can grow unbounded under high load

**Neutral:**
- Events are Python dataclass instances — serialization is manual for persistence
- Priority queue adds complexity — only a few event types use it

#### Future Impact

- Event schemas should be versioned from the start (every event includes a `version` field)
- Consider persisted event store for full crash recovery (ADR-0006)
- If IPC is needed between frontend and backend, use HTTP bridging, not a second Event Bus
- Event Catalog (`docs/34-EVENT_CATALOG.md`) must be maintained alongside code changes

#### Related ADRs

- [ADR-0006](#adr-0006-persistence--sqlite-with-vector-extensions): SQLite persistence for events
- [ADR-0011](#adr-0011-execution-engine--deterministic-state-machine): Execution engine consumes events
- [ADR-0013](#adr-0013-activity-center--event-backed-notification-feed): Activity center subscribes to events

---

### ADR-0003: AI Router — Multi-Provider Strategy with Fallback

**Status:** Adopted · Active  
**Date:** 2026-05-10  
**Author:** Engineering Lead  
**Theme:** Intelligence

#### Decision

Implement an **AI Router** using the **Strategy pattern** with:
- **Strategy types:** cost-optimized, latency-optimized, performance-optimized, fallback
- **Provider abstraction:** unified interface for `chat`, `chat_stream`, `embed`, `health_check`
- **Failover Manager:** automatic provider fallback with circuit breaker
- **Circuit breaker:** 3 consecutive failures → 30s cooldown → half-open → closed
- **Provider matrix:** local Ollama (free), OpenAI, Anthropic, custom providers
- **Capability-based routing:** simple queries → local, complex → cloud, vision → multimodal models
- **Rate limiting:** per-provider, configurable (default: 60 req/min, 100k tokens/min)

#### Context

Eve OS must support multiple AI providers because:
- No single provider offers the best quality/cost/latency for all queries
- Local models (Ollama) provide privacy and offline capability
- Cloud models (GPT-4, Claude) provide superior reasoning for complex tasks
- Provider outages must not block the user
- Different tasks have different model requirements (chat, vision, embedding, code)

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Single provider** | Single point of failure. Vendor lock-in. No offline capability. |
| **Round-robin** | No awareness of model capabilities. Routes vision queries to text-only models. |
| **Manual provider selection** | Poor UX — users shouldn't need to know which model to use. |
| **AI decides provider** | Unpredictable, can't guarantee security or cost boundaries. |

#### Consequences

**Positive:**
- Automatic failover means provider outages are invisible to users
- Cost optimization routes simple queries to free local models
- Latency optimization routes interactive queries to fastest provider
- Circuit breaker prevents cascading failures
- New providers can be added without changing the routing logic
- Rate limiting prevents accidental cost overruns

**Negative:**
- Strategy pattern adds complexity — 4 routing strategies to maintain
- Provider capability matrix must be kept up to date
- Circuit breaker tuning is application-specific and may need adjustment
- Local model quality varies significantly by hardware

**Neutral:**
- Router adds ~20-50ms to each AI request (strategy evaluation time)
- Provider API differences must be normalized in the abstraction layer

#### Future Impact

- Plugin SDK should allow third-party provider implementations
- Consider caching for identical queries (deduplication)
- Provider cost tracking needed for user-facing analytics
- Streaming responses require careful provider abstraction

#### Related ADRs

- [ADR-0004](#adr-0004-capability-registry--planner-tool-decoupling): Router feeds into Planner via Capability Registry
- [ADR-0011](#adr-0011-execution-engine--deterministic-state-machine): Execution engine manages AI interaction state

---

### ADR-0004: Capability Registry — Planner-Tool Decoupling

**Status:** Adopted · Active  
**Date:** 2026-05-15  
**Author:** Engineering Lead  
**Theme:** Architecture

#### Decision

Introduce a **Capability Registry** as an intermediary layer between the Planner and Tool Manager. The Planner:
- Never imports or knows specific tool IDs
- Queries the Capability Registry with a task description
- Receives ranked capability matches
- Constructs execution plans from capability references

The registry:
- Stores capability metadata (id, name, description, tags, permission level, version)
- Ranks matches using weighted scoring: `id (1.5x) + name (1.2x) + description (1.0x) + tags (0.8x)` against task description
- Uses `SequenceMatcher` for fuzzy word matching
- Supports conflict resolution: `quality (0.4) + context (0.3) + version (0.2) + permission (0.1)`
- Supports versioning via Semver — multiple versions of same capability coexist

#### Context

The v1.0 architecture freeze identified that the Planner had a direct dependency on Tool Manager. This created tight coupling — adding a new tool required changing the Planner. The architecture review (ARCHITECTURE_REVIEW_REPORT.md) mandated decoupling.

The system has 16 tool modules and 24+ predefined capabilities. New tools and plugins will continue to be added. The Planner needs to discover what's available without knowing implementation details.

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Hardcoded tool list in Planner** | Brittle. Every new tool requires Planner changes. Violates Open-Closed Principle. |
| **AI decides tools** | Unpredictable. Bypasses permission system. Can't guarantee deterministic planning. |
| **Tool Manager as discovery** | Creates circular dependency — Planner depends on Tool Manager, tools depend on Planner results. |

#### Consequences

**Positive:**
- Planner is completely decoupled from tool implementations
- New tools and plugins register their capabilities without Planner changes
- Conflict resolution enables graceful handling of overlapping capabilities
- Versioning supports gradual capability evolution
- Fuzzy matching handles natural language task descriptions

**Negative:**
- Registry adds latency to plan construction (~5-15ms per query)
- Weight tuning is heuristic — may return suboptimal matches at the boundary
- SequenceMatcher is O(n*m) — large registries may need optimization
- Registry must be kept in sync with actual tool availability

**Neutral:**
- Capability definitions are duplicated metadata (once in registry, once in tool)
- Plugin capabilities must be registered at install time

#### Future Impact

- ADR-0016 describes a future plugin-powered registry with dynamic capability discovery
- Consider machine learning for capability matching (beyond fuzzy string matching)
- Registry could be extended with capability cost estimates for cost-aware planning

#### Related ADRs

- [ADR-0003](#adr-0003-ai-router--multi-provider-strategy-with-fallback): AI Router output feeds into Planner
- [ADR-0011](#adr-0011-execution-engine--deterministic-state-machine): Planner creates execution plans from capabilities
- [ADR-0016](#adr-0016-capability-registry-future--plugin-powered-discovery): Future evolution of this decision

---

### ADR-0005: Permission System — Four-Tier Progressive Model

**Status:** Adopted · Active  
**Date:** 2026-05-20  
**Author:** Security Lead  
**Theme:** Security

#### Decision

Implement a **four-tier permission system**:

| Level | Name | Behaviour | Examples |
|-------|------|-----------|---------|
| 0 | Read | Auto-grant, no prompt | Read file, clipboard, system info |
| 1 | Safe | Auto-grant, logged | Write files, execute commands |
| 2 | Workspace | Session confirm (once per session) | Install plugin, modify registry |
| 3 | Sensitive | Always confirm | Delete files, access credentials, network |

Additional policies:
- Session permissions expire after configurable timeout (default: 300s)
- Permission level per tool is configurable via `config/default.yaml`
- Default-deny for any tool without an explicit level assignment
- All permission decisions are audited to SQLite
- Admin mode bypasses all prompts (configurable)

#### Context

Eve OS executes arbitrary tools on the user's system — reading files, running commands, modifying registry, accessing the network. The user must remain in control. A binary allow/deny model is too coarse (users would either allow everything or deny everything). A full manual model is too friction-heavy (every operation requires confirmation).

The model must:
- Protect the user from malicious or erroneous operations
- Minimise friction for safe, frequent operations
- Be understandable at a glance
- Support session-based trust for multi-step workflows

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Binary allow/deny** | Too coarse. Users would either allow everything (unsafe) or deny everything (app unusable). |
| **Full manual (prompt for everything)** | Too much friction. Reading a file doesn't need confirmation every time. |
| **Full automatic** | Unsafe. No user control over sensitive operations. |
| **Capability-based only** | Confusing — users don't think in terms of "capability grants." |

#### Consequences

**Positive:**
- Progressive trust matches user expectations: read is free, delete is protected
- Session permissions reduce friction for multi-step workflows
- Configurable defaults allow power users to tune the balance
- Audit log provides full accountability
- Default-deny ensures safety for unclassified operations

**Negative:**
- Four levels add complexity to the permission evaluation logic
- Session timeout is a compromise — too short frustrates, too long risks safety
- Permission configuration UI must clearly explain each level
- Plugin permissions must map to the same four-tier model

**Neutral:**
- Permission level boundaries are somewhat arbitrary and may need adjustment
- Some tools span multiple levels depending on their arguments (e.g., `write /tmp/foo` vs `write C:/Windows/system32`)

#### Future Impact

- Plugin SDK must enforce the same permission model in sandboxed processes
- Consider per-file or per-directory permission overrides for fine-grained control
- Machine learning could predict permission intent and reduce prompts

#### Related ADRs

- [ADR-0011](#adr-0011-execution-engine--deterministic-state-machine): Permission check is a state in the execution state machine
- [ADR-0015](#adr-0015-authentication--local-first-device-identity): Authentication underpins permission identity

---

### ADR-0006: Persistence — SQLite with Vector Extensions

**Status:** Adopted · Active  
**Date:** 2026-05-25  
**Author:** Engineering Lead  
**Theme:** Persistence

#### Decision

Use **SQLite** as the primary data store with:
- **Zero configuration** — no server, no setup, no daemon
- **Single file** database at `~/.aios/aios.db`
- **JSON1 extension** for flexible schema (JSON columns with queryable paths)
- **Vector extension** (`sqlite-vec`) for embedding-based semantic search
- **WAL mode** for concurrent read performance
- **AES-256-GCM encryption** for sensitive data at rest
- **Foreign keys** with CASCADE for referential integrity

#### Context

Eve OS is a desktop application, not a web service. It needs a data store that:
- Requires zero setup or administration from the user
- Works offline with no network dependency
- Can store structured data (conversations, tools, plugins) and semi-structured data (configurations, metadata)
- Supports semantic search via vector embeddings
- Is reliable and portable across Windows installations

The database schema covers 11 tables: conversations, messages, tools, tool_calls, permission_requests, memories, memory_tags, plugins, plugin_tools, plugin_configs, contexts, events, settings.

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **PostgreSQL** | Requires a server process. Overkill for a single-user desktop app. ~100MB installer impact. |
| **MongoDB** | Complex setup. No native Windows embedded version at the time of decision. |
| **JSON files** | No querying capability. Concurrent access issues. No schema enforcement. |
| **DuckDB** | Analytics-oriented, not optimized for point queries. Smaller ecosystem. |
| **Dexie.js (IndexedDB)** | Browser-only. Loses Python backend access to data. |

#### Consequences

**Positive:**
- Zero-configuration — database is created automatically on first launch
- Single file — easy to back up, copy, or migrate
- JSON1 extension enables flexible schema evolution without migrations
- Vector extension enables semantic search alongside structured queries
- WAL mode allows concurrent reads without blocking writes
- Good performance for desktop-scale data (< 1M rows per table)

**Negative:**
- SQLite is single-writer — concurrent write contention under high load
- Vector extension is community-maintained (not part of official SQLite)
- Full-text search requires FTS5 extension (separate consideration)
- Encryption requires additional library (`sqlcipher` or custom AES)
- No built-in replication or sync for multi-device scenarios

**Neutral:**
- Schema migrations are manual SQL scripts (no ORM migrations)
- All timestamps are ISO 8601 UTC, all IDs are UUID v4

#### Future Impact

- Consider `sqlcipher` for transparent encryption if file-level encryption is insufficient
- Vector search performance should be benchmarked at 10k, 100k, and 1M embedding scales
- If multi-device sync is needed, SQLite replication is limited — consider LiteFS or custom sync

#### Related ADRs

- [ADR-0007](#adr-0007-memory-architecture--temporal-knowledge-graph): Memory system uses SQLite for persistence
- [ADR-0002](#adr-0002-event-bus--in-process-async-message-bus): Event history optionally persisted to SQLite

---

### ADR-0007: Memory Architecture — Temporal Knowledge Graph

**Status:** Proposed  
**Date:** 2026-06-01  
**Author:** Memory System Owner

#### Decision

Model memory as a **temporal knowledge graph** with:
- **4 super types:** Action, Knowledge, Entity, Meta
- **12+ edge types:** relates_to, depends_on, leads_to, part_of, similar_to, contradicts, references, caused_by, follows, precedes, derived_from, associated_with
- **Typed nodes:** each memory entry has a type, subtype, super type, importance, confidence, tags, timestamp, source
- **Temporal by default:** every node and edge has creation time, last accessed time, and optional expiry
- **Append-only:** memories are never deleted, only archived or marked inactive
- **Bidirectional edges:** every edge is stored twice (source → target, target → source)
- **Storage adapters:** SQLite (primary), Vector (embeddings), File (large blobs), Object Store (serialised data)
- **Search:** keyword, type, project, date range, tags, status, relationship traversal, semantic (vector)

#### Context

The existing Memory System (`memory_system.py`) uses a flat memory model with simple types (FACT, PREFERENCE, LEARNING, PATTERN) and in-memory short-term storage combined with SQLite-backed long-term storage. As the system scales to thousands of memories with complex relationships between them, a more sophisticated model is needed.

The Architecture Review identified that:
- Flat memory models lose relationship information
- Without typed edges, querying "what led to this result" is impossible
- Importance decay and archival are needed to manage graph size
- Plugin-specific memory types must be supported

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Flat memory (current)** | No relationships between entries. Can't answer "why" or "how" queries. |
| **Vector DB only** | Good for similarity search, poor for structured queries and relationship traversal. |
| **Relational DB only** | Good for structured queries, poor for semantic similarity and flexible schemas. |
| **Graph DB (Neo4j)** | External dependency, heavy for a desktop app, requires server process. |

#### Consequences

**Positive:**
- Rich relationship queries: "what did I learn after installing X?"
- Pluggable storage adapters allow optimised backends per use case
- Type system enables domain-specific memory handling (plugin memory types)
- Temporal model supports time-based queries and decay
- Append-only preserves full history for debugging and recovery

**Negative:**
- Graph size grows unbounded — requires importance decay and auto-archival
- Complex queries require traversal algorithms (BFS, DFS) — not trivial
- Bidirectional edges double storage requirements
- Vector + SQLite + graph hybrid is complex to maintain
- No existing Python library provides all three (graph + vector + SQL) in one package

**Neutral:**
- First implementation is an MVP with SQLite + in-memory graph
- Storage adapter pattern allows replacing backends without changing query interface

#### Future Impact

- Memory pruning and archival strategy is critical — must be tested at scale
- Cross-reference integrity between projects/agents must be maintained
- Plugin type registration must be idempotent and versioned
- Consider adding a vector-first adapter (Pinecone, Chroma) for cloud deployments

#### Related ADRs

- [ADR-0008](#adr-0008-memory-core--zero-dependency-graph-subsystem): Core graph implementation of this architecture
- [ADR-0006](#adr-0006-persistence--sqlite-with-vector-extensions): SQLite adapter for memory storage
- [ADR-0004](#adr-0004-capability-registry--planner-tool-decoupling): Memory capabilities registered in Capability Registry

---

### ADR-0008: Memory Core — Zero-Dependency Graph Subsystem

**Status:** Adopted · Active  
**Date:** 2026-06-10  
**Author:** Memory System Owner  
**Supersedes:** Initial implementation of memory core (pre-ADR)

#### Decision

Implement the Memory Core as a **zero-dependency, framework-agnostic graph subsystem** with:

- **7 subsystems:**
  1. Registry — type metadata and provider management
  2. Graph — in-memory node/edge storage with adjacency dual-indexing
  3. Store — facade over graph operations
  4. Query — keyword, type, relationship, and semantic search
  5. Traversal — graph navigation (BFS, DFS, pathfinding)
  6. Events — pub-sub for memory mutations
  7. Validation — constraint checking for all operations

- **Key design principles:**
  - Zero external dependencies (pure Python/stdlib only)
  - Zero coupling to UI, backend, or persistence layers
  - Framework-agnostic — usable from React, CLI, tests, or backend adapters
  - In-memory graph with Map-based storage
  - Immutable nodes and edges (never mutated in place)
  - Queries never mutate state (pure functions)
  - Events are immutable dataclasses
  - Module-level singletons for convenience, but any caller can instantiate their own

- **14+ invariants** for correctness (node uniqueness, edge type validation, type registration ordering, etc.)

#### Context

The Memory Core is the foundation of the Memory Architecture (ADR-0007). It must be:
- Independently testable without a database or UI
- Embeddable in any Python application or test suite
- Strictly deterministic for reproducibility
- Thread-safe (at minimum, safe for asyncio concurrency)
- The single source of truth for memory state during a session

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **NetworkX** | External dependency. Not designed for persistence or long-running applications. Performance issues at scale. |
| **sqlite3-backed directly** | Couples graph logic to persistence. Harder to test. Loses in-memory query performance. |
| **Custom ORM** | Over-engineered. Most operations are graph traversals, not SQL queries. |
| **DuckDB + graph extension** | External dependency, analytics-oriented, smaller ecosystem. |

#### Consequences

**Positive:**
- Zero dependencies means zero supply-chain risk for this critical subsystem
- Immutable operations prevent subtle mutation bugs
- Pure query functions are trivially testable and cacheable
- Framework-agnostic design means the core can be reused in any context (backend, CLI, plugin, test)
- Type system provides compile-time-like safety for graph operations
- Dual-indexed adjacency enables O(1) edge lookups

**Negative:**
- In-memory only — does not persist by itself (requires storage adapters)
- No built-in persistence, encryption, or vector search (by design — separate concerns)
- Module-level singletons create hidden global state in tests if not properly isolated
- Custom implementation lacks the optimization of production graph databases

**Neutral:**
- 7-subsystem decomposition is more files to maintain but clearer separation of concerns
- Provider Contract pattern adds boilerplate for type registration

#### Future Impact

- Storage adapters (SQLite, vector DB, file) are separate modules that read/write through the Store facade
- The core can be published as a standalone Python package for plugin authors
- Performance at >100k nodes should be benchmarked — may need indexing optimizations
- The Provider Contract enables third-party type extensions

#### Related ADRs

- [ADR-0007](#adr-0007-memory-architecture--temporal-knowledge-graph): Parent architecture this core implements
- [ADR-0006](#adr-0006-persistence--sqlite-with-vector-extensions): Persistence adapter for this core

---

### ADR-0009: Frontend Architecture — State-Driven Workspace Registry

**Status:** Adopted · Active  
**Date:** 2026-06-15  
**Author:** Frontend Lead  
**Theme:** Frontend Architecture

#### Decision

Structure the frontend as a **state-driven workspace registry** with:

- **No client-side routing library** — workspaces are driven by React state, not URL paths
- **Workspace registry pattern:** `App.tsx` owns a `workspace` state variable; registered workspaces (Chat, Activity) render based on current workspace
- **Overlay system:** Settings, Plugins, Tools, Vision panels render as absolute-positioned overlays over the workspace
- **Command palette** as a global overlay (triggered by keyboard shortcut, not navigation)
- **Theme state:** `useState<"dark" | "light">` at the App root, toggled by user preference
- **Global keyboard shortcuts** registered at App level (Ctrl+K, Ctrl+P, Ctrl+T, Ctrl+M, Ctrl+I, Ctrl+,)
- **No React Router, no URL-based navigation, no browser history**

#### Context

Eve OS is a desktop application rendered in a Tauri webview — not a web page. The frontend:
- Has a fixed window size (no browser resize, no mobile)
- Has no URL bar (no deep linking, no back/forward buttons)
- Has a small number of views (Chat, Activity, Settings, Plugins, Tools, Vision)
- Uses overlays and modals for secondary views (no page transitions)
- Must feel like a desktop app, not a web app

Using a client-side routing library (React Router, TanStack Router) would introduce unnecessary complexity and URL-management overhead for a non-web application.

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **React Router** | Designed for URL-driven web apps. Adds bundle size (~14KB). URL management is meaningless in a webview with no address bar. |
| **TanStack Router** | Type-safe, but still URL-oriented. Over-engineered for 5 views. |
| **State machine-based (XState)** | Powerful but adds ~20KB and significant conceptual overhead for what is essentially a tabbed interface. |
| **Single-page with hidden divs** | Maintains all views in DOM simultaneously. Performance concerns. No lazy loading. |

#### Consequences

**Positive:**
- Zero routing library dependencies — smaller bundle, less complexity
- Workspace state is trivially testable — no route mocking needed
- Overlays are simpler than nested route layouts
- Keyboard shortcuts are the primary navigation mechanism (consistent with power-user UX)
- Theme and workspace state are co-located at the App root — single source of truth

**Negative:**
- No URL-based deep linking — can't link to a specific workspace externally
- No browser history — back button doesn't navigate workspaces (irrelevant in a desktop app, but matters for embedded web scenarios)
- Workspace switching requires state management — no out-of-the-box animated transitions
- Adding a new workspace requires modifying App.tsx (no dynamic workspace registration from plugins — future concern)

**Neutral:**
- The workspace registry could be extracted to a custom hook (`useWorkspace`) for testability
- Plugin-contributed workspaces would require dynamic registry registration (not yet implemented)

#### Future Impact

- Plugin-contributed workspaces will require a dynamic workspace registry (beyond current static App.tsx)
- If deep linking becomes necessary (e.g., notifications that open a specific workspace), a lightweight hash-based router could be added
- The overlay system will need z-index management as more overlays are added

#### Related ADRs

- [ADR-0001](#adr-0001-desktop-shell--tauri--python-sidecar): Desktop shell hosting this frontend
- [ADR-0012](#adr-0012-command-center--keyboard-first-universal-palette): Command palette as the primary navigation interface
- [ADR-0010](#adr-0010-design-system--css-custom-property-tokens): Design system used by all frontend components

---

### ADR-0010: Design System — CSS Custom Property Tokens

**Status:** Adopted · Active  
**Date:** 2026-06-20  
**Author:** Frontend Lead  
**Theme:** Design System

#### Decision

Build the design system on **CSS custom properties** with:

- **Token categories:**
  - Color: base, semantic, surface, execution state tokens
  - Typography: font family, font size (xs through 3xl), weight, line height
  - Spacing: 4px-based scale (1 through 16)
  - Border radius: sm (4px), md (8px), lg (12px), xl (16px), full (9999px)
  - Shadows: sm, md, lg (with dark/light overrides)
  - Z-index: dropdown (100), overlay (1000), modal (1100)
  - Animation: duration (fast/normal/slow), easing (standard/decelerate/emphasized)
  - Surface: primary, secondary, sidebar, floating, overlay, elevated, panel

- **Theme strategy:**
  - Dark theme as `:root` (default)
  - Light theme as `.light` class override
  - No `prefers-color-scheme` media query (user toggle, not system)
  - All component colors derive from 9 base tokens

- **Component primitives** (CSS classes, not React components):
  - `pr-btn-*`, `pr-input-*`, `pr-card-*`, `pr-badge-*`, `pr-surface-*`, `pr-panel-*`
  - `pr-msg-*`, `pr-composer-*`, `pr-exec-*`, `pr-sidebar-*`
  - `pr-dialog-*`, `pr-empty-state-*`, `pr-loading-state-*`, `pr-error-state-*`
  - `mw-*` (memory workspace), `pr-cmd-*`, `pr-inspector-*`, `pr-activity-*`

- **No runtime CSS-in-JS:** all styling via plain CSS files (tokens.css, primitives.css, globals.css)

#### Context

Eve OS has a React frontend with 80+ components across 18 categories. A consistent visual language is essential. The team evaluated several approaches to design systems before deciding on CSS custom properties.

Key requirements:
- Dark + light theme with complete coverage of all components
- Component-specific styling without framework lock-in
- Low runtime overhead (no style recalculation on theme switch)
- Developer-friendly — easy to add new tokens and component variants
- Framework-agnostic tokens that could be used in a different view layer if React is replaced

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Styled Components** | Runtime CSS-in-JS. Slower theme switching (recalculates all components). Vendor lock-in. |
| **Tailwind CSS only** | Excellent for rapid development but token abstraction is lost in utility classes. Tokens.css was preferred for design-system-level abstraction. (Tailwind is used alongside, not instead of.) |
| **CSS Modules** | Component-scoped but no built-in theming. Requires additional tooling for theme switching. |
| **Material UI / Chakra / Radix** | Heavy (~50-100KB+). Hard to customise to Eve's unique aesthetic. Version lock-in risk. |
| **Vanilla Extract / Linaria** | Zero-runtime CSS-in-JS but adds build tooling and framework coupling. |

#### Consequences

**Positive:**
- Themes switch by toggling a CSS class — no JavaScript style recalculation
- All design tokens are in plain CSS — inspectable in DevTools, overridable by themes
- Zero runtime overhead — no JavaScript execution for styling
- Framework-agnostic — tokens.css can be used with any view layer
- Component primitives provide consistency without forcing a specific component API
- 80+ components share the same token system, ensuring visual consistency

**Negative:**
- No type-safe token access — developers must know token names (mitigated by IDE autocomplete and token reference)
- No dead token elimination — all tokens are in the CSS bundle regardless of usage
- Component primitives are CSS-only — no associated React component logic or TypeScript validation
- Theming is class-based (`.light`) rather than context-based — can't nest themes

**Neutral:**
- Tailwind is available alongside tokens for utility needs — dual approach requires discipline
- CSS bundles grow with the component catalog — no tree-shaking for CSS

#### Future Impact

- Consider design token TypeScript export for programmatic access (color manipulation, chart libraries)
- Container queries will enable responsive component variants without media queries
- The `.pr-*` and `.mw-*` class naming convention can be extended for plugin-contributed components

#### Related ADRs

- [ADR-0009](#adr-0009-frontend-architecture--state-driven-workspace-registry): Frontend consuming this design system
- Full token reference: `docs/06_Design_System.md`
- Component catalog: `docs/05_Component_Catalog.md`

---

### ADR-0011: Execution Engine — Deterministic State Machine

**Status:** Adopted · Active  
**Date:** 2026-06-25  
**Author:** Execution Engine Owner  
**Theme:** Execution

#### Decision

Model the execution system as a **deterministic state machine** with:

- **11 execution states:** Idle, Listening, Thinking, Planning, PermissionCheck, Executing, Responding, Speaking, Error, Recovery, Cancelled
- **20+ validated state transitions** — only explicitly allowed transitions are permitted
- **State properties per node:** timeout, auto-recovery strategy, user notification requirement
- **Execution graph** supports parallel steps (DAG, not linear chain)
- **Recovery strategies per failure type:**
  - Transient: auto-retry with exponential backoff (3 attempts)
  - Expected: fallback to alternative capability
  - Critical: graceful degradation with user notification
  - Fatal: clean shutdown with state preservation
- **Progress tracking** via `ProgressEvent` — percentage, current step, estimated remaining
- **Circuit breaker** per tool: 3 consecutive failures → 60s cooldown
- **Permission check** is a state in the machine — execution pauses at PermissionCheck, resumes on grant

#### Context

Eve OS executes complex multi-step workflows that involve AI, tools, plugins, and user interaction. The execution system must:
- Guarantee deterministic behaviour (same input → same state transitions)
- Handle failures gracefully at every step
- Support user interruption (cancel, permission deny)
- Provide real-time progress updates to the UI
- Integrate with the Permission System, Planner, Tool Manager, and Event Bus

The existing execution code was spread across multiple modules without a unified state machine. The Architecture Review mandated a formal state machine for correctness and observability.

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Implicit state (if/else)** | Unmaintainable. No single source of truth for valid transitions. Impossible to audit. |
| **XState / pytransitions** | External dependencies. XState is JavaScript-only. pytransitions adds ~20KB and framework coupling. |
| **Database-driven state machine** | Adds latency for every state transition. Over-engineered for a single-user desktop app. |
| **Actor model (Thespian / Pykka)** | Heavy concurrency model. More complexity than needed for sequential tool execution. |

#### Consequences

**Positive:**
- Deterministic transitions make the execution flow predictable and testable
- Recovery strategies are explicit and per-type — no ad-hoc error handling
- Progress tracking enables rich UI feedback (progress bar, current step, ETA)
- Permission check as a state means the machine naturally pauses and resumes
- Circuit breaker prevents cascading tool failures
- Parallel execution graph enables efficient multi-tool workflows

**Negative:**
- 11 states + 20+ transitions is complex to implement and test
- Recovery strategies must be defined for every possible failure point — easy to miss one
- State machine adds ~5-15ms overhead per transition (negligible for typical workflows)
- UI must handle all possible states gracefully — missing state handling leads to confusing UX

**Neutral:**
- State machine is implemented in Python (backend), not TypeScript (frontend)
- Frontend receives state updates via Event Bus events — never manages state directly
- The state machine pattern enables formal verification of transition correctness

#### Future Impact

- Plugin execution should be expressed as sub-state-machines within the main execution flow
- Long-running workflows may need persistence of state machine snapshots (crash recovery)
- The state machine could be visualised for debugging (state graph → SVG)

#### Related ADRs

- [ADR-0004](#adr-0004-capability-registry--planner-tool-decoupling): Planner creates execution plans consumed by the state machine
- [ADR-0005](#adr-0005-permission-system--four-tier-progressive-model): Permission check state integrates with the Permission System
- [ADR-0002](#adr-0002-event-bus--in-process-async-message-bus): State machine publishes events consumed by UI and monitoring

---

### ADR-0012: Command Center — Keyboard-First Universal Palette

**Status:** Adopted · Active  
**Date:** 2026-07-01  
**Author:** Frontend Lead  
**Theme:** Command Center

#### Decision

Implement the **Command Palette** as the primary command interface with:

- **Global shortcut:** Ctrl+K opens the palette from any workspace
- **Fuzzy search:** matches command names, descriptions, and keywords
- **Categorised results:** commands grouped by category (Navigation, Tools, Memory, System)
- **Keyboard-first navigation:** ArrowUp/ArrowDown to select, Enter to execute, Escape to close
- **Mouse fallback:** click to execute (but keyboard is the primary interaction model)
- **Command history:** last 50 executed commands persisted across sessions
- **Empty state:** helpful message when no commands match ("Try: open settings, search memory, run tool")
- **Result actions:** commands can return results that are displayed inline or open a workspace
- **Lazy-loaded categories:** commands loaded on demand by category to keep startup fast

#### Context

Eve OS targets power users and developers who prefer keyboard shortcuts over mouse navigation. The sidebar provides visual navigation to 2 workspaces (Chat, Activity), but users need fast access to 100+ commands across tools, plugins, memory, settings, and system operations.

A command palette is the standard pattern for power-user applications (VS Code, Slack, Linear, Raycast, Alfred). It must be:
- Fast: sub-100ms search for 200+ commands
- Discoverable: users can browse available commands
- Extensible: plugins can register their own commands
- Consistent: same interaction model regardless of command type

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Sidebar navigation only** | Doesn't scale beyond a few items. No search. Poor discoverability. |
| **Toolbar + menu bar** | Traditional desktop pattern. Takes screen space. Mouse-dependent. |
| **Natural language input** | The comet (
  query + typo tolerance + natural language understanding)/barrel file for each com, too imprecise for exact actions. Already handled by the chat interface. |
| **Voice commands only** | Less reliable, slower, not suitable for all environments. |

#### Consequences

**Positive:**
- Fast access to 100+ commands without leaving the keyboard
- Fuzzy search makes commands discoverable without memorising exact names
- Category grouping helps users browse available functionality
- Plugin-registered commands automatically appear in the palette
- Command history enables quick re-execution of frequent actions
- Works for both novice users (browsing categories) and power users (direct search)

**Negative:**
- Fuzzy search over 200+ commands requires efficient indexing (~5-10ms per query)
- Plugin-registered commands must be loaded lazily — plugin startup adds latency to first search
- Commands with arguments need a secondary interface (modal or inline form)
- Command palette is a global overlay — must not conflict with other keyboard shortcuts

**Neutral:**
- Command palette is accessible from any workspace — must handle context-dependent commands
- Some commands may require permission — permission flow must integrate with command execution

#### Future Impact

- Plugin-contributed commands must support the same fuzzy-search and categorisation
- Consider command chaining (pipe output of one command to another)
- The palette could become the primary launcher for all Eve functionality, replacing the sidebar for power users
- Machine learning could rank commands by usage frequency and recency

#### Related ADRs

- [ADR-0009](#adr-0009-frontend-architecture--state-driven-workspace-registry): Command palette is a global overlay in the workspace registry
- [ADR-0011](#adr-0011-execution-engine--deterministic-state-machine): Command execution flows through the execution engine

---

### ADR-0013: Activity Center — Event-Backed Notification Feed

**Status:** Adopted · Active  
**Date:** 2026-07-05  
**Author:** Frontend Lead  
**Theme:** Activity

#### Decision

Implement the **Activity Center** as a consolidated notification feed powered by the Event Bus:

- **Subscription model:** Activity Center subscribes to Event Bus events and renders them as a chronological feed
- **Event-to-activity mapping:** specific event types map to activity items (tool_execution:completed → activity entry, permission_request:granted → activity entry)
- **Real-time updates:** new events appear immediately in the feed via Event Bus subscription
- **Unread badge:** activity icon in header shows unread count badge
- **Filterable:** filter by event type, severity, date range
- **Actionable:** activity items can have action buttons (retry failed tool, review permission grant)
- **Dismissible:** individual items or all items can be dismissed (hidden, not deleted)
- **Persisted:** activity history survives restart (backed by SQLite)
- **Badge variants:** colour-coded by severity (success, warning, error, info)

#### Context

Eve OS operates autonomously — running tools, checking permissions, executing plans, and interacting with the user. The user needs a way to:
- See what Eve has done recently
- Review the results of executed tools
- Respond to permission requests
- Catch up on events that happened while they were away
- Filter signal from noise in a busy execution session

The Event Bus (ADR-0002) already carries all system events. The Activity Center is the user-facing presentation layer for those events.

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Toast notifications only** | Ephemeral — user can't review past activity. No history. |
| **Execution log only** | Too detailed. Shows raw events, not meaningful activity summaries. |
| **Email/push notifications** | Desktop app doesn't need external notification infrastructure. |
| **Separate notification system** | Duplicates Event Bus. Every event would fire twice (Event Bus + Notification Bus). |

#### Consequences

**Positive:**
- No separate notification infrastructure — reuses Event Bus subscription
- Real-time updates without polling
- Chronological feed provides a complete activity history
- Filterable by event type — users can focus on what matters
- Actionable items enable quick response (retry, review)
- Persisted history means users don't lose context after restart

**Negative:**
- Event-to-activity mapping must be maintained as new event types are added
- High-volume event types (e.g., streaming cursor updates, typing indicator) must be filtered out
- Unread badge count requires tracking "last viewed" timestamp per user session
- Activity history grows unbounded — archival/purging strategy needed

**Neutral:**
- Activity items are derived from events, not stored independently — event schema changes affect activity rendering
- Some events may contain sensitive data — activity must respect permission levels

#### Future Impact

- Activity Center could become a notification hub with per-event-type notification preferences
- Consider notification grouping (collapse "retried 3 times" into one item)
- Plugin events should automatically appear in the activity feed (via Event Bus subscription)

#### Related ADRs

- [ADR-0002](#adr-0002-event-bus--in-process-async-message-bus): Activity Center subscribes to Event Bus events
- [ADR-0009](#adr-0009-frontend-architecture--state-driven-workspace-registry): Activity is a registered workspace in the App shell

---

### ADR-0014: Inspector — Reactive Session Detail Panel

**Status:** Adopted · Active  
**Date:** 2026-07-10  
**Author:** Frontend Lead  
**Theme:** Inspector

#### Decision

Implement the **Inspector** as a reactive detail panel for execution sessions with:

- **Tabbed interface:** Permissions, Summary, Timeline, Tools, Logs, Metadata, Performance
- **Reactive data binding:** panel content updates in real-time as the session progresses
- **Session selection:** clicking an execution in the ExecutionThread opens its details in the Inspector
- **Read-only detail view:** no in-panel editing — modifications go through the original execution flow
- **Tab-specific content:**
  - **Permissions:** permission requests and grants for the session
  - **Summary:** brief overview of what happened and the result
  - **Timeline:** chronological view of all steps in the session
  - **Tools:** which tools were used, their inputs and outputs
  - **Logs:** raw log output for debugging
  - **Metadata:** session ID, timestamps, duration, models used
  - **Performance:** timing breakdown of each step
- **Event-driven updates:** subscribes to session-specific events via Event Bus

#### Context

When Eve executes a multi-step workflow, users need to understand what happened, why, and what the results were. The ExecutionThread shows a compact history of sessions, but each session contains dozens of steps, tool calls, permission requests, and log entries. A dedicated detail panel is needed for deep inspection.

Key requirements:
- Must handle session detail for active (in-progress) and completed sessions
- Must support inspection of sessions with 100+ steps
- Must respect permission levels (some session details may be sensitive)
- Must work with both AI-initiated and user-initiated sessions

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Expandable inline details** | Would make the ExecutionThread unreasonably long. Poor UX for complex sessions. |
| **Modal dialog** | Blocks interaction with the rest of the UI. Can't reference session details while working. |
| **Dedicated page/workspace** | Navigation overhead. Users need quick access while staying in context. |
| **External log viewer** | Context switch. Loses integration with execution flow. |

#### Consequences

**Positive:**
- Side panel allows concurrent viewing of session list + session details
- Real-time updates let users watch a session progress while reading its Inspector
- Tabbed organisation keeps complex sessions manageable
- Performance tab enables debugging without external profiling tools
- Reactive data binding means no manual refresh

**Negative:**
- 7 tabs is a lot of surface area — each tab must be maintained and tested
- Real-time updates for active sessions require careful event subscription management
- Sessions with 100+ steps may render slowly in the Timeline tab
- Inspector state (which session, which tab) is not persisted across restarts

**Neutral:**
- Inspector is read-only — all actions happen in the ExecutionThread or Command Center
- Session data is served from the backend event log — Inspector is purely a UI concern

#### Future Impact

- Plugin-specific Inspector tabs could enrich tool-specific execution details
- Consider Inspector extensibility for plugin-contributed session types
- The Performance tab could integrate with a future benchmarking system

#### Related ADRs

- [ADR-0011](#adr-0011-execution-engine--deterministic-state-machine): Execution engine produces the session data consumed by Inspector
- [ADR-0002](#adr-0002-event-bus--in-process-async-message-bus): Inspector subscribes to session-specific events

---

### ADR-0015: Authentication — Local-First Device Identity

**Status:** Draft  
**Date:** 2026-07-15  
**Author:** Security Lead  
**Theme:** Authentication

#### Decision

Adopt a **local-first authentication model** with no cloud dependency:

- **No cloud accounts:** Eve OS does not require user registration, login, or any cloud account
- **Device-level identity:** identity is derived from the machine (machine ID hash + application salt)
- **No remote authentication server:** all authentication is local
- **Plugin authentication:** plugins authenticate via a device-bound token (not a user login)
- **Local encryption key:** derived from device identity + user-provided passphrase (optional)
- **Session isolation:** each running instance has its own authentication context — no cross-instance identity sharing
- **Administrator mode:** optional elevated privileges for system-level operations (Windows UAC integration)

#### Context

Eve OS is a privacy-first, local-first desktop AI assistant. The Vision document states: *"Privacy-first: Everything runs locally by default. No data leaves without explicit permission."* Requiring a cloud account for authentication would contradict this principle.

However, the system still needs to:
- Identify the user for permission decisions
- Encrypt data at rest with a device-bound key
- Authenticate plugin operations
- Provide an optional admin mode for system-level operations
- Support future multi-user scenarios (family, shared workstation)

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Cloud account (OAuth, email/password)** | Violates privacy-first principle. Requires backend infrastructure. Creates a central point of compromise. |
| **Biometric** | Hardware-dependent. Not available on all Windows devices. Can't be the sole auth method. |
| **Passphrase-only** | Too simple. No device binding means database can be decrypted on another machine. |
| **No authentication at all** | Unsafe. No identity for permission decisions. No encryption key derivation. |

#### Consequences

**Positive:**
- No server infrastructure to maintain
- No user data ever touches a cloud service unless explicitly opted in
- Device-bound encryption key means database is tied to a specific machine
- Works fully offline with no dependencies on external auth providers
- No account recovery, password reset, or SSO integration to build

**Negative:**
- No cross-device identity — database can't be moved to another machine without a migration tool
- No user authentication for multi-user scenarios (requires a future ADR)
- Machine ID is a weak identifier — can be spoofed by sophisticated malware
- Administrator mode requires Windows UAC integration (complex, varies by Windows version)
- Plugin developers can't authenticate users — all plugin identity is device-bound

**Neutral:**
- Encryption key derivation (machine ID + passphrase) is well-understood (PBKDF2, Argon2)
- UAC integration is Windows-specific — cross-platform support would need a different approach

#### Future Impact

- Multi-user support will require a significant auth model revision — design with extensibility in mind
- Cloud features (sync, sharing, remote access) would require adding cloud authentication alongside local auth
- The device-bound model limits enterprise deployment scenarios (centralised identity management)

#### Related ADRs

- [ADR-0005](#adr-0005-permission-system--four-tier-progressive-model): Permission decisions are based on authenticated identity
- [ADR-0006](#adr-0006-persistence--sqlite-with-vector-extensions): Database encryption key is derived from device identity

---

### ADR-0016: Capability Registry (Future) — Plugin-Powered Dynamic Discovery

**Status:** Draft  
**Date:** 2026-07-20  
**Author:** Engineering Lead  
**Theme:** Future Capability Registry

#### Decision

Extend the current Capability Registry (ADR-0004) to support **plugin-powered dynamic capability discovery** with:

- **Plugin capability registration:** plugins declare capabilities in their manifest (`plugin.yaml`) — automatically registered on install
- **Dynamic discovery:** registry discovers capabilities at startup and when plugins are installed/uninstalled — no code changes needed
- **Weighted conflict resolution:** when multiple plugins offer the same capability, resolution uses: `quality (0.4) + version (0.2) + freshness (0.2) + user preference (0.2)`
- **Capability marketplace:** future capability to browse and install capabilities from a registry (analogous to VS Code extensions)
- **Deprecation API:** capability owners can mark capabilities as deprecated with a sunset date
- **Capability metering:** usage tracking per capability for analytics and quality scoring
- **Sandboxed capability execution:** plugin-provided capabilities run in sandboxed subprocesses (using Plugin Isolator)
- **Capability composition:** capabilities can depend on other capabilities (e.g., "code_review" depends on "git_diff" + "file_read")

#### Context

The current Capability Registry (ADR-0004) is a static catalog of built-in capabilities. As the plugin ecosystem grows, capabilities must become dynamic:
- Plugins should declare capabilities without modifying the registry code
- Users should be able to install new capabilities by installing plugins
- Conflicting capabilities from different plugins must be resolved intelligently
- Deprecated capabilities should gradually phase out without breaking existing plans
- Capability quality should improve over time based on usage data

This is a future ADR — the infrastructure described here is not yet implemented. It establishes the target architecture for the capability system.

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| **Static registry (current)** | Every new capability requires a code change. Doesn't scale to a plugin ecosystem. |
| **AI discovers capabilities** | Unpredictable. Can't guarantee capability availability. No conflict resolution. |
| **Capability per plugin (no registry)** | No cross-plugin capability resolution. Users must know which plugin provides which capability. |

#### Consequences

**Positive:**
- Plugin ecosystem can grow without changes to the core registry
- Conflict resolution enables graceful handling of overlapping plugin capabilities
- Capability composition enables powerful multi-step capabilities built from simpler ones
- Deprecation API enables gradual capability evolution
- Usage metering provides data for quality improvements

**Negative:**
- Dynamic registration adds complexity — capability loading at startup, plugin install, and plugin uninstall
- Conflict resolution may produce unexpected results (user installs two plugins that claim the same capability differently)
- Capability composition introduces dependency management — circular dependencies must be detected
- Sandboxed execution adds latency to capability invocation (~50-200ms per call)
- Usage metering raises privacy considerations — must be opt-in and local-only by default

**Neutral:**
- Plugin capability registration is an extension of the existing plugin manifest format
- Sandboxed execution reuses the Plugin Isolator infrastructure

#### Future Impact

- A capability marketplace would require a server-side registry (contradicts local-first principle unless optional)
- Capability composition could lead to complex dependency graphs — consider DAG validation
- Quality scoring requires a feedback mechanism — user ratings, success/failure tracking, execution time

#### Related ADRs

- [ADR-0004](#adr-0004-capability-registry--planner-tool-decoupling): Current static registry that this extends
- [ADR-0011](#adr-0011-execution-engine--deterministic-state-machine): Planner queries this registry for capability resolution

---

## 4. Appendix A — ADR Template

Use this template for all new ADRs:

```markdown
### ADR-NNN: Title

**Status:** [Draft | Proposed | Adopted | Active | Superseded | Deprecated | Rejected]
**Date:** YYYY-MM-DD
**Author:** [Owner Name]
**Theme:** [Theme Name]

#### Decision

_What was decided, in one paragraph. Specific, actionable, and unambiguous._

#### Context

_What problem needed solving. What constraints existed. What factors influenced the decision._

#### Alternatives Considered

| Alternative | Reason Rejected |
|-------------|----------------|
| _Option A_ | _Why A wasn't chosen_ |
| _Option B_ | _Why B wasn't chosen_ |

#### Consequences

**Positive:**

- _Upside 1_
- _Upside 2_

**Negative:**

- _Downside 1_
- _Downside 2_

**Neutral:**

- _Neutral observation 1_

#### Future Impact

_What this decision enables or constrains in the future. What follow-up decisions it may trigger._

#### Related ADRs

- _ADR-NNN: Related decision 1_
- _ADR-NNN: Related decision 2_
```

---

## 5. Appendix B — Decision Theme Index

| Theme | ADRs | Key Decisions |
|-------|------|---------------|
| **Desktop Packaging** | 0001, 0016 | Tauri shell, Python sidecar, installer strategy |
| **Infrastructure** | 0002 | In-process async event bus |
| **Intelligence** | 0003 | Multi-provider AI routing, circuit breaker |
| **Architecture** | 0004, 0016 | Capability Registry, Planner-Tool decoupling |
| **Security** | 0005, 0015 | Four-tier permissions, local-first identity |
| **Persistence** | 0006 | SQLite with vector extensions |
| **Memory** | 0007 | Temporal knowledge graph |
| **Memory Core** | 0008 | Zero-dependency graph subsystem |
| **Frontend Architecture** | 0009 | State-driven workspace registry |
| **Design System** | 0010 | CSS custom property tokens |
| **Execution** | 0011 | Deterministic state machine |
| **Command Center** | 0012 | Keyboard-first command palette |
| **Activity** | 0013 | Event-backed notification feed |
| **Inspector** | 0014 | Reactive session detail panel |
| **Authentication** | 0015 | Device-bound local identity |
| **Future Capability Registry** | 0016 | Plugin-powered dynamic discovery |

---

## 6. Appendix C — Superseded ADRs

No ADRs have been superseded at this time. This section will track ADRs that have been replaced by newer decisions.

| Superseded ADR | Superseded By | Date | Reason |
|----------------|---------------|------|--------|
| — | — | — | — |

---

*This ADR log is maintained as the authoritative architectural history of Eve OS. Every engineer is responsible for proposing ADRs for architectural decisions and updating existing ADRs when decisions change.*
