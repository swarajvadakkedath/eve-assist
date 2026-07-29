# ADR 0007: Memory Architecture — Knowledge Graph Design

**Status:** Proposed
**Date:** 2026-07-20
**Author:** Architecture Team

---

## Executive Summary

Eve's memory is a **temporal knowledge graph** of typed nodes and edges that models everything Eve knows about the user's work. It is not a vector database, not a chat log, and not a filesystem index. It is a semantic network where every object is related to every other object through explicit, typed relationships.

This document defines the conceptual model, domain objects, relationship types, lifecycle, ownership, search, and extensibility — without prescribing storage, query language, or implementation framework.

---

## 1. Core Design Philosophy

### Memory is not storage

Memory is a **semantic model** of the user's work context. Storage (SQLite, vector index, filesystem) is an implementation detail below this architecture.

### First Principles

| Principle | Meaning |
|-----------|---------|
| **Everything is connected** | No isolated objects. Every node has at least one edge. |
| **Edges are first-class** | Relationships carry types, timestamps, weights, and metadata. |
| **Temporal by default** | Every node and edge carries creation time. The graph is append-only with soft-delete. |
| **Typed nodes** | Nodes have immutable types. Types define allowed edge schemas. |
| **Pluggable types** | Future modules register new node and edge types via a type registry. |
| **Projects scope memory** | Every node belongs to exactly one project. Cross-project links are allowed. |
| **Derivation over duplication** | Knowledge is extracted from source nodes, not copied. References preserve provenance. |

### What Memory Is Not

- **Not chat history** — Conversations are a source of memory, not memory itself
- **Not a vector database** — Embeddings are a search index, not the data model
- **Not a filesystem** — Files are referenced, not stored in memory
- **Not a database schema** — The conceptual model is independent of storage

---

## 2. Architecture Diagram (ASCII)

```
+======================================================================+
|                         MEMORY ARCHITECTURE                          |
+======================================================================+

  MEMORY CLIENTS
  +------------+  +------------+  +------------+  +------------+
  | Command    |  | Activity   |  | Context    |  | AI Router  |
  | Center     |  | Center     |  | Engine     |  |            |
  +-----+------+  +-----+------+  +-----+------+  +-----+------+
        |               |               |               |
  +-----+---------------+-------------------------------+--------+
  |                    MEMORY API                                     |
  |  +-----------+  +-----------+  +-----------+  +--------------+  |
  |  | CRUD      |  | Traversal |  | Search    |  | Subscription |  |
  |  | Operations|  | (GraphQL) |  | (Filters) |  | (Events)     |  |
  |  +-----------+  +-----------+  +-----------+  +--------------+  |
  +------------------------------------------------------------------+
        |               |               |               |
  +-----+---------------+-------------------------------+--------+
  |                    MEMORY CORE                                     |
  |  +----------------+  +--------------+  +-----------------------+  |
  |  | Graph Engine   |  | Type Registry|  | Importance / Decay   |  |
  |  | (Nodes + Edges)|  | (Pluggable)  |  | Engine               |  |
  |  +----------------+  +--------------+  +-----------------------+  |
  |  +----------------+  +--------------+  +-----------------------+  |
  |  | Indexer        |  | Relationship |  | Derivation Pipeline  |  |
  |  | (Keyword/Full) |  | Inferencer   |  | (Summaries, Facts)   |  |
  |  +----------------+  +--------------+  +-----------------------+  |
  +------------------------------------------------------------------+
        |               |               |               |
  +-----+---------------+-------------------------------+--------+
  |                    STORAGE ADAPTERS                               |
  |  +-----------+  +-----------+  +-----------+  +--------------+  |
  |  | SQLite    |  | Vector    |  | File      |  | Object Store |  |
  |  | (Primary) |  | (Embed)   |  | (Blobs)   |  | (Future)     |  |
  |  +-----------+  +-----------+  +-----------+  +--------------+  |
  +------------------------------------------------------------------+

  MODULE CONTRIBUTORS
  +----------+ +----------+ +----------+ +----------+ +----------+
  | Browser  | | Voice    | | Vision   | | Plugins  | | Workflows|
  | Module   | | Module   | | Module   | | (Any)    | | Module   |
  +----------+ +----------+ +----------+ +----------+ +----------+
        |            |            |           |             |
  Each module registers node types, edge types, and contributes
  memory objects through the Memory API.
```

---

## 3. Domain Model

### Core Concepts

```
+------------------------------------------------------------------+
|                     MEMORY DOMAIN MODEL                           |
+------------------------------------------------------------------+

  MemoryNode (abstract)
    |
    +-- ActionNode (things Eve DOES)
    |     +-- Conversation
    |     +-- Execution
    |     +-- Workflow
    |     +-- BrowserSession
    |     +-- VoiceSession
    |     +-- PluginAction
    |
    +-- KnowledgeNode (things Eve KNOWS)
    |     +-- Artifact
    |     +-- KnowledgeStatement
    |     +-- Reference
    |     +-- Note
    |     +-- VisionCapture
    |     +-- Template
    |
    +-- EntityNode (things that EXIST)
    |     +-- Person
    |     +-- Organization
    |     +-- Location
    |     +-- File
    |     +-- Folder
    |     +-- Bookmark
    |
    +-- MetaNode (things that ORGANIZE)
          +-- Project
          +-- Collection
          +-- Tag
          +-- Preference
          +-- Reminder
          +-- Task

  Edge (typed, directed, temporal)
    |
    +-- CONTAINS         (parent-child)
    +-- PRODUCES         (creation)
    +-- DERIVES_FROM     (origin/source)
    +-- REFERENCES       (external or internal reference)
    +-- RELATES_TO       (undirected association)
    +-- SEQUENCES        (ordering)
    +-- CONTRIBUTES_TO   (aggregation)
    +-- CONFIGURES       (preference binding)
    +-- PINNED           (user prominence)
    +-- ARCHIVED         (lifecycle state)
    +-- OWNED_BY         (project membership)
    +-- CUSTOM           (module-defined)
```

### 3.1 Action Nodes

Things Eve does. These are the primary sources of memory.

| Type | Definition | Key Properties |
|------|-----------|----------------|
| **Conversation** | A user-AI interaction session | participants, messageCount, duration, topic |
| **Execution** | A tool or command invocation | action, parameters, result, exitCode, duration |
| **Workflow** | A reusable sequence of executions | steps, trigger, schedule, runCount |
| **BrowserSession** | A browser automation session | url, actions, duration, pages |
| **VoiceSession** | A voice interaction session | transcript, commands, duration |
| **PluginAction** | Any plugin-defined action | pluginId, actionType, payload |

### 3.2 Knowledge Nodes

Things Eve knows. These are derived from or created by action nodes.

| Type | Definition | Key Properties |
|------|-----------|----------------|
| **Artifact** | Any output produced by an execution | mimeType, size, location, hash |
| **KnowledgeStatement** | An extracted fact or summary | content, confidence, source |
| **Reference** | A pointer to external content | uri, title, description, fetchTime |
| **Note** | User-authored text | content, pinned, format |
| **VisionCapture** | A screenshot or camera capture | imageRef, ocrText, annotations |
| **Template** | A reusable prompt or action pattern | type, body, variables, usageCount |

### 3.3 Entity Nodes

Things that exist in the user's world.

| Type | Definition | Key Properties |
|------|-----------|----------------|
| **Person** | A person known to the system | name, contactInfo, relationship |
| **Organization** | A company, team, or group | name, domain, role |
| **Location** | A physical or virtual place | name, coordinates, type |
| **File** | Any file on the filesystem | path, mimeType, size, hash |
| **Folder** | A directory | path, purpose |
| **Bookmark** | A saved URL | url, title, favicon |

### 3.4 Meta Nodes

Things that organize other memory.

| Type | Definition | Key Properties |
|------|-----------|----------------|
| **Project** | Top-level organizational container | name, description, status, icon |
| **Collection** | A user-defined grouping | name, description, itemCount |
| **Tag** | A lightweight label | name, color, usageCount |
| **Preference** | A user configuration value | scope, key, value |
| **Reminder** | A time-based notification | time, message, repeat |
| **Task** | An action item | status, priority, dueDate, assignee |

---

## 4. Relationship Diagram

```
                       PROJECT
                      (CONTAINS)
                          |
        +--------+--------+--------+--------+-------+
        |        |        |        |        |       |
   CONVERSATION  EXECUTION  WORKFLOW  COLLECTION  PREFERENCE
        |        |        |
   (PRODUCES)   (PRODUCES)  (CONTAINS)
        |        |        |
   KNOWLEDGE   ARTIFACT   EXECUTION
   STATEMENT     |           |
        |   (REFERENCES)  (SEQUENCES)
        |        |           |
        +--------+-----------+--------+--------+
        |        |        |        |        |
     PERSON   ORGANIZATION  FILE    NOTE   REFERENCE
        |
   (RELATES_TO)
        |
    CONVERSATION, EXECUTION, ARTIFACT, etc.

    Edge rules:
    - PROJECT CONTAINS all nodes
    - CONVERSATION PRODUCES KnowledgeStatement (summary)
    - EXECUTION PRODUCES Artifact (output files)
    - EXECUTION DERIVES_FROM Conversation (if user-requested)
    - Any node REFERENCES File (on filesystem)
    - Any node RELATES_TO any other node (user-defined)
    - WORKFLOW CONTAINS Execution instances
    - COLLECTION REFERENCES nodes (user-curated grouping)
    - PREFERENCE CONFIGURES Project, Conversation, Module
```

### Edge Cardinality

| Edge Type | From | To | Count |
|-----------|------|----|-------|
| CONTAINS | Project | Any | 1:N |
| CONTAINS | Workflow | Execution | 1:N |
| PRODUCES | Action | Knowledge | 1:N |
| DERIVES_FROM | Knowledge | Action | N:1 |
| REFERENCES | Any | Reference | N:1 |
| REFERENCES | Any | File | N:1 |
| RELATES_TO | Any | Any | N:N |
| SEQUENCES | Execution | Execution | 1:1 |
| CONTRIBUTES_TO | Session | KnowledgeStatement | N:1 |
| CONFIGURES | Preference | Any | N:1 |
| PINNED | User | Node | N:N |
| ARCHIVED | System | Node | N:1 |
| OWNED_BY | Node | Project | N:1 |

---

## 5. Lifecycle

### 5.1 Node Lifecycle

```
     +-----------+
     |  CREATED  |  -- Initial state on first persistence
     +-----+-----+
           |
     +-----v-----+
     |  ACTIVE   |  -- Normal operational state
     +-----+-----+
           |
     +-----v--------+
     |  REFERENCED  |  -- Linked by one or more edges
     +-----+--------+
           |
     +-----v-----+
     |  UPDATED  |  -- Content changed (preserves history)
     +-----+-----+
           |
     +-----v------+
     |  ARCHIVED  |  -- Not active, fully preserved
     +-----+------+
           |
     +-----v------+
     |  DELETED   |  -- Soft-delete (reversible)
     +------------+
```

### 5.2 Edge Lifecycle

Edges are append-only. Once created, an edge is never modified or deleted. Deactivation is expressed by adding a new edge with status `deactivated` or by creating a `SUPERSEDES` edge.

### 5.3 Version History

Every update to a node creates a **version record**:
- Previous state is preserved
- Timestamped
- Author recorded (user or system)
- Diff available

### 5.4 Importance and Decay

Each node carries:
- **importanceScore** (0.0–1.0, computed or user-set)
- **accessCount** — number of times referenced
- **lastAccessTime** — time of last traversal
- **decayRate** — per-type default, overridable

The importance engine periodically:
- Scores nodes based on access patterns
- Suggests archival for low-importance, old nodes
- Boosts recently-accessed nodes in search

---

## 6. Ownership Model

### 6.1 Hierarchical Ownership (Lifecycle)

```
PROJECT owns all nodes within it.
  - Deleting a project cascades to all contained nodes (soft delete)
  - Nodes cannot exist outside a project
  - A global "DEFAULT" project exists for unassigned memory
```

### 6.2 Peer Relationships (Discovery)

```
All nodes are peers in the graph.
  - Discovery traverses edges, not ownership
  - Any node can link to any other node, regardless of project
  - Cross-project links are explicitly allowed
  - Search spans all projects (or can be scoped)
```

### 6.3 Trade-offs

| Model | Advantage | Disadvantage |
|-------|-----------|-------------|
| **Hierarchical** | Clean lifecycle, easy backup, predictable deletion | Can create silos, rigid |
| **Peer graph** | Maximum discoverability, flexible | Complex lifecycle, garbage collection needed |
| **Hybrid (chosen)** | Clean lifecycle + maximum discoverability | Requires both ownership index and graph index |

### 6.4 Concrete Rules

1. Every node has exactly one `OWNED_BY` edge to a Project
2. Projects cannot be nested (flat hierarchy)
3. Any node may have edges to nodes in other projects
4. Collections are project-scoped (cannot span projects)
5. Tags are global (cross-project by default)

---

## 7. Search Model

### 7.1 Dimensions

| Dimension | Implementation | Latency |
|-----------|---------------|---------|
| **Keyword** | Full-text index on node content and metadata | < 100ms |
| **Type** | Filter by node type | < 10ms |
| **Project** | Scope by project ID | < 10ms |
| **Date range** | Filter by createdAt, updatedAt | < 50ms |
| **Tags** | Filter by associated tags | < 50ms |
| **Status** | Filter by lifecycle status (active, archived, etc.) | < 10ms |
| **Favorites/Pinned** | Filter by PINNED edge | < 10ms |
| **Recent** | Sort by lastAccessTime | < 50ms |
| **Relationship** | Graph traversal from seed node | < 200ms |
| **Semantic** | Embedding similarity (future) | < 500ms |

### 7.2 Query Patterns

```
Pattern 1: "Find me the file from that conversation yesterday"
  Node: Conversation → traverse PRODUCES edges → filter type=Artifact

Pattern 2: "Show me everything related to Project X"
  Seed: Project → traverse CONTAINS edges → return all descendants

Pattern 3: "What executions produced this artifact?"
  Seed: Artifact → traverse PRODUCES (reverse) → filter type=Execution

Pattern 4: "Find conversations about the payment API"
  Full-text search on Conversation nodes → filter by topic/keywords

Pattern 5: "What was I working on last Tuesday?"
  Filter by date range → sort by importance/recency

Pattern 6: "Show me all knowledge related to this workflow"
  Seed: Workflow → traverse CONTAINS → traverse PRODUCES → filter type=KnowledgeStatement
```

### 7.3 Search Architecture

```
+-------------------+     +-------------------+     +-------------------+
| Query Parser      |     | Query Planner     |     | Result Assembler  |
| (parses intent)   | --> | (chooses strategy)| --> | (merges, scores)  |
+-------------------+     +--------+----------+     +-------------------+
                                   |
              +--------------------+-------------------+
              |                    |                   |
     +--------v-------+   +-------v--------+   +------v--------+
     | Keyword Index   |   | Graph Traversal|   | Embedding     |
     | (full-text)     |   | (edge walking) |   | Index (future)|
     +-----------------+   +----------------+   +---------------+
```

### 7.4 Result Ranking

Results are ranked by a composite score:
- Text relevance (keyword match density)
- Importance score (0.0–1.0)
- Recency (time since last access, inverse exponential)
- Edge count (nodes with more connections rank higher)
- User boost (explicit PINNED or FAVORITE)

---

## 8. Project Organization

### 8.1 Project as Primary Container

```
Project
  +-- Info (name, description, status, created, modified)
  +-- Conversations
  +-- Executions
  +-- Workflows
  +-- Artifacts (output files, generated content)
  +-- Knowledge (extracted facts, summaries, entities)
  +-- Sessions (browser, voice, vision)
  +-- Notes (user-authored)
  +-- References (bookmarks, URLs)
  +-- Templates (prompts, patterns)
  +-- Collections (user-defined groups)
  +-- Tasks
  +-- Reminders
  +-- Preferences (project-scoped)
```

### 8.2 Advantages

| Advantage | Explanation |
|-----------|-------------|
| **Lifecycle clarity** | Delete project = delete its memory, no orphan nodes |
| **Backup granularity** | Project-level export/import |
| **Context switching** | Open project = load its memory, hide others |
| **Access control** | Future multi-user: project-scoped permissions |
| **Organization** | Users naturally think in projects |

### 8.3 Disadvantages

| Disadvantage | Mitigation |
|--------------|------------|
| **Cross-project links require explicit support** | Allow edges across project boundaries. Graph traversal follows edges regardless of project. |
| **Global memory (favorites, people) spans projects** | Global "DEFAULT" project for unbound items. Tags are global. |
| **Empty project feels like lost memory** | Default project auto-collects all unassigned memory. Users can organize later. |

### 8.4 File Organization

```
Memory is organized by project in the conceptual model, not in the filesystem.
Storage is flat (UUID-based) with a project_index for scoping.
```

---

## 9. Future Extensibility

### 9.1 Module Type Registration

Any future module extends memory by registering with the Type Registry:

```
Module:
  1. Call registerNodeType("moduleName:CustomNode", schema)
  2. Call registerEdgeType("moduleName:CustomEdge", schema)
  3. Call registerEdgeRules("CustomNode", allowedEdges)
  4. Module creates/publishes memory via Memory API
```

### 9.2 Module Memory Contributions

| Module | Node Types | Edge Types |
|--------|-----------|------------|
| **Browser** | BrowserSession, Bookmark, Download | NAVIGATES_TO, DOWNLOADS, BOOKMARKS |
| **Voice** | VoiceSession, VoiceCommand | TRANSCRIBES, EXECUTES_COMMAND |
| **Vision** | VisionCapture, Annotation | CAPTURES, ANNOTATES |
| **Files** | File (already core), Folder (already core) | STORES, CONTAINS (folder) |
| **Plugins** | PluginAction (already core) | EXECUTES_PLUGIN, CUSTOM |
| **Workflows** | Workflow (already core) | TRIGGERS, COMPOSES |
| **Settings** | Preference (already core) | CONFIGURES |

### 9.3 Extensibility Guarantees

1. **No schema migration needed** for new types — types are registered at runtime
2. **No code changes to core** — the graph engine is type-agnostic
3. **No API versioning issues** — new types extend the API, don't modify existing contracts
4. **Storage is flexible** — new types use the same node/edge tables with JSON payloads

### 9.4 Long-term Evolution

| Capability | When | Architecture Impact |
|-----------|------|-------------------|
| **Embeddings** | Now (foundation) | Add embedding index, no model change |
| **Semantic Search** | Phase 1 | Query planner adds embedding branch |
| **Knowledge Graph Reasoning** | Phase 2 | Inference engine walks edges + embeddings |
| **Long-term Memory** | Phase 2 | Importance decay auto-archives. Episodic compression summarizes old memories. |
| **Multi-user** | Phase 3 | Add owner edge. Project-scoped permissions. |
| **Distributed Sync** | Phase 3 | Append-only log. Conflict resolution on edges. |
| **Memory Federation** | Phase 4 | Cross-machine graph merge. Identity resolution for People nodes. |
| **Automatic Curation** | Phase 4 | AI agent traverses graph, suggests links, summarizes, archives. |

---

## 10. Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Graph size grows unbounded** | Medium | Importance decay + auto-archival. Soft-delete. User-configurable retention. |
| **Query performance degrades with graph size** | Medium | Index on critical dimensions. Limit traversal depth. Pagination. Async for expensive queries. |
| **Cross-project links create orphan references** | Low | Soft-delete preserves edges. Garbage collector identifies stale references. |
| **Type proliferation from modules** | Low | Type registry with namespacing. Review process for built-in types. |
| **User confusion from too much connectivity** | Medium | Relevance scoring. Default views show high-importance connections. User can hide noise. |
| **Memory becomes stale** | Low | Periodic re-indexing. Confidence decay on old knowledge. User can refresh/update. |
| **Storage migration needed** | Low | Storage adapters abstract the backend. Schema versioning. |
| **Embedding model changes require re-indexing** | Low | Embedding version field. Background re-indexing. No data loss. |

---

## 11. Recommended APIs

### 11.1 Core CRUD

```
Nodes:
  createNode(type, properties, projectId) → Node
  getNode(nodeId) → Node
  updateNode(nodeId, properties) → Node (versioned)
  archiveNode(nodeId) → Node
  deleteNode(nodeId) → Node (soft)
  getNodeHistory(nodeId) → Version[]
  getRelatedNodes(nodeId, edgeTypes?, depth?) → Node[]

Edges:
  createEdge(type, sourceId, targetId, properties?) → Edge
  getEdges(nodeId, direction?, type?) → Edge[]
  deleteEdge(edgeId) → void (soft)

Projects:
  createProject(name, properties?) → Project
  getProject(projectId) → Project
  getProjectGraph(projectId, depth?) → Subgraph
  deleteProject(projectId) → void (cascading soft delete)
```

### 11.2 Search

```
search(query, filters?) → ResultSet
  filters: type[], projectId[], tags[], dateRange, status, pinned

searchByRelationship(seedNodeId, edgeTypes?, filters?) → ResultSet
  Traverse edges from seed, filter, rank, return.

recent(limit?, projectId?) → Node[]
  Ordered by lastAccessTime descending.

favorites(projectId?) → Node[]
  Nodes with PINNED edge.

timeline(startDate, endDate, projectId?) → Event[]
  Chronological events: create, update, link, archive.
```

### 11.3 Command Center Integration

```
Command                    → Memory Action
────────────────────────────────────────────────────
memory:search <query>      → search(query)
memory:recent              → recent(20)
memory:pinned              → favorites()
memory:project:open <name> → getProject(name). setContext(project)
memory:related <nodeId>    → getRelatedNodes(nodeId, depth=2)
memory:save                → createNode("Note", ...)
memory:archive <nodeId>    → archiveNode(nodeId)
memory:forget <nodeId>     → deleteNode(nodeId)
```

### 11.4 Activity Center Integration

```
Event Type            → Activity Display
─────────────────────────────────────────
memory.node.created   → "New knowledge captured: {summary}"
memory.node.updated   → "{type} updated: {title}"
memory.edge.created   → "Linked {source} → {target}"
memory.node.archived  → "{title} archived"
memory.node.deleted   → "{title} removed"
memory.import.complete → "Imported {count} items from {project}"
```

---

## 12. Example User Journeys

### Journey 1: Research Session

```
1. User asks: "Research the FastAPI documentation"
2. Conversation created (ActionNode)
3. BrowserSession created (ActionNode)
4. Pages visited → Bookmark nodes (EntityNode)
5. User asks: "Summarize the key points"
6. KnowledgeStatement created (KnowledgeNode)
   - DERIVES_FROM → Conversation
   - DERIVES_FROM → BrowserSession
   - REFERENCES → Bookmark nodes
7. User asks: "Save this as a reference"
8. Collection "FastAPI Research" created
   - CONTAINS → KnowledgeStatement
   - CONTAINS → Bookmark references
9. User opens memory search next week
   - Types "FastAPI" → finds KnowledgeStatement
   - Traverses edges → finds original Conversation
   - Traverses more edges → finds BrowserSession, Bookmarked pages
```

### Journey 2: Debugging a Bug

```
1. User asks: "Find the bug in payment.py"
2. Conversation created
3. Execution: "read payment.py" → Artifact (file content)
4. Execution: "run test_payment.py" → Artifact (test output)
5. Conversation continues with debugging
6. KnowledgeStatement: "Bug found: incorrect tax calculation in line 142"
7. KnowledgeStatement: REFERENCES → File("payment.py")
8. User asks: "Save this workflow for later"
9. Workflow created from the execution sequence
   - CONTAINS → Execution nodes (ordered)
   - Note added describing the fix
10. Next week, similar bug appears
    - User searches "tax calculation"
    - Finds KnowledgeStatement
    - Finds Workflow
    - Re-runs workflow with one parameter change
```

### Journey 3: Cross-Project Discovery

```
1. Project A: "Eve Frontend" — conversations about React components
2. Project B: "Eve Backend" — conversations about API design
3. A KnowledgeStatement in Project A: "API endpoint expects snake_case"
   - REFERENCES → a Conversation in Project B
4. Months later, user is in Project C: "Eve Mobile"
   - Searches "API format"
   - Finds KnowledgeStatement from Project A
   - Traverses REFERENCES edge → finds Project B Conversation
   - Finds the original API discussion
   - Discovery crosses project boundaries automatically
```

### Journey 4: Plugin Extending Memory

```
1. A "GitHub" plugin registers:
   - nodeType: "github:PR", "github:Issue", "github:Commit"
   - edgeType: "github:REVIEWS", "github:FIXES"
2. User works on a PR through the plugin
3. Memory is created:
   - github:PR node
   - github:Commit nodes
   - github:REVIEWS edges
   - DERIVES_FROM → Conversation (the discussion)
4. User searches "PR #42"
   - Found directly via type filter + keyword
   - Also found via "what changed last week" → embedded in timeline
   - Also found via "what's related to this file" → edge traversal
5. No core code changes needed — plugin works within the existing graph
```

---

## 13. Migration Strategy

### Phase 0: Current State

Existing `12-Memory-System.md` defines short-term, long-term, and semantic memory as opaque buckets. The current SQLite schema has generic tables for conversations, executions, and events.

### Phase 1: Graph Foundation

1. Introduce the graph data model alongside existing storage
2. Migrate existing conversations into MemoryNode:Conversation with CONTAINS edges to Project:Default
3. Migrate existing executions into MemoryNode:Execution
4. Run in dual-write mode for one release cycle

### Phase 2: Knowledge Extraction

1. Build the derivation pipeline (Conversation → KnowledgeStatement)
2. Add the Type Registry
3. Enable module registration
4. Add the importance/decay engine

### Phase 3: Client Integration

1. Wire Command Center to Memory API
2. Wire Activity Center to Memory events
3. Add memory search UI
4. Add memory graph visualization

### Phase 4: Advanced Features

1. Embedding index for semantic search
2. Relationship inference (AI-suggested edges)
3. Memory curation dashboard
4. Cross-device sync

### Rollback Strategy

- Dual-write in Phase 1 means the old storage remains valid
- Each phase has a toggle to fall back to previous behavior
- Graph data can be rebuilt from source action nodes

---

## 14. Recommendations

### Adopt

1. **Graph model** — Typed nodes and edges as the universal memory representation
2. **Project as primary container** — With cross-project link support
3. **Pluggable type registry** — Modules extend the model, not the engine
4. **Hybrid ownership** — Hierarchical lifecycle + peer discovery
5. **Append-only edges** — Immutable relationships with soft-deactivation
6. **Temporal everything** — Every node and edge carries time
7. **Importance scoring** — Active curation prevents unbounded growth

### Defer

1. **Distributed sync** — Not until multi-machine support is needed
2. **Multi-user permissions** — Not a v1 concern
3. **Federation** — Requires identity resolution, deferred to Phase 4
4. **Automatic curation** — AI-powered graph maintenance, deferred

### Reject

1. **Folders as primary organization** — Tags + Collections + Project provides sufficient structure
2. **Document-oriented storage** — Graph edges are essential for discoverability
3. **Global namespace without projects** — All memory in one flat graph is overwhelming
4. **Synchronous derivation** — Knowledge extraction should be async, non-blocking

---

## Appendix A: Type Registry Schema (Conceptual)

```
registerNodeType:
  name: string              # e.g., "browser:Bookmark"
  superType: enum           # action | knowledge | entity | meta
  properties:               # schema for the node's data payload
    - name: string
      type: string          # string | number | boolean | datetime | json
      required: boolean
  edges:                    # allowed edge types from this node
    fromType: string[]      # which edge types can originate here
    toType: string[]        # which edge types can target here

registerEdgeType:
  name: string              # e.g., "browser:BOOKMARKS"
  fromTypes: string[]       # allowed source node types
  toTypes: string[]         # allowed target node types
  properties:               # schema for edge metadata
    - name: string
      type: string
      required: boolean
```

---

## Appendix B: Comparison with Alternatives

| Approach | Discoverability | Lifecycle Clarity | Extensibility | Complexity |
|----------|----------------|-------------------|---------------|------------|
| **Graph (chosen)** | High | High | High | Medium |
| Relational tables | Low | Medium | Low | Low |
| Document store | Medium | Low | Medium | Low |
| Hybrid RAG (vector-only) | Medium | None | Low | Medium |
| Flat files + index | Low | None | Medium | Low |
| Event log only | High | None | High | High (replay needed) |

The graph approach offers the best balance of discoverability, lifecycle clarity, and extensibility for a long-lived AI operating system memory model.

---

*This document defines the conceptual architecture only. Storage, query language, implementation framework, and API routes are determined in separate implementation specifications.*
