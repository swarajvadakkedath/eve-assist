# ADR-008 — Memory Core Contract

**Status:** Adopted  
**Date:** 2026-07-20  
**Version:** 1.0.0  
**Deciders:** Architecture Team  
**References:** ADR-007 (Graph Model), Phase 8A Implementation  

---

## 1 Executive Summary

The Memory Core is the domain layer for managing Eve OS's persistent knowledge graph. It provides an in-memory graph database with typed nodes and edges, a type registry system, query engine with filtering and traversal, event bus, and validation — all with zero external dependencies and zero coupling to UI, backend, or persistence.

The core is organized into seven subsystems: Registry (type metadata), Graph (node/edge storage), Store (facade), Query (search), Traversal (graph navigation), Events (pub-sub), and Validation (constraint checking). Every subsystem is a plain class — no frameworks, no singletons required, no React dependency.

---

## 2 Goals

- Provide a graph data model where nodes represent memories and edges represent relationships
- Enforce type safety through a registry-based type system
- Enable querying by keyword, type, tag, source, date range, importance, confidence, status, and traversal
- Support BFS/DFS graph traversal with path finding and cycle detection
- Emit typed events for every mutation so consumers stay in sync
- Validate all inputs against registered types and range constraints
- Be framework-agnostic: usable from React, CLI, tests, or backend adapters

---

## 3 Non-Goals

- Persistence to disk or database
- Remote sync or multi-user
- Real-time streaming or delta push
- Full-text search engine (keyword search is in-memory linear scan)
- UI components, React bindings, or hooks
- Authorization or access control
- Backend API layer or REST endpoints
- Plugin loading or dynamic registration at runtime

---

## 4 Architecture Overview

```
MemoryRegistry
  ├── NodeTypeRegistry    — node type definitions
  └── EdgeTypeRegistry    — edge type definitions

MemoryGraph
  ├── nodes: Map<string, MemoryNode>
  ├── edges: Map<string, MemoryEdge>
  ├── adjacencyOut: Map<string, Set<string>>
  └── adjacencyIn:  Map<string, Set<string>>

RelationshipEngine
  ├── delegates to MemoryGraph
  └── delegates to MemoryRegistry

GraphTraversal
  └── delegates to MemoryGraph

MemoryEventBus
  ├── typed subscriptions
  ├── wildcard subscriptions (onAny)
  └── event history (ring buffer)

MemorySelectors
  └── delegates to MemoryGraph

QueryEngine
  ├── uses QueryParser
  ├── uses GraphTraversal
  └── uses MemorySelectors

MemoryStore
  ├── aggregates Graph + Registry + EventBus + Selectors + Query
  └── bridges Graph change notifications → EventBus events

MemoryValidation
  └── uses NodeTypeRegistry + EdgeTypeRegistry

GraphUtils
  └── pure functions, no class
```

### Dependency Graph

```
MemoryStore
  ├── MemoryGraph (composition)
  ├── MemoryRegistry (composition)
  ├── MemoryEventBus (composition)
  ├── MemorySelectors (composition)
  ├── QueryEngine (composition)
  ├── GraphTraversal (composition)
  └── RelationshipEngine (composition)

QueryEngine
  ├── MemoryGraph (injection)
  ├── MemorySelectors (injection)
  ├── GraphTraversal (composition)
  └── QueryParser (composition)

RelationshipEngine
  ├── MemoryGraph (injection)
  ├── MemoryRegistry (injection)
  └── GraphTraversal (composition)

MemorySelectors
  └── MemoryGraph (injection)

GraphTraversal
  └── MemoryGraph (injection)

MemoryValidation
  ├── NodeTypeRegistry (injection)
  └── EdgeTypeRegistry (injection)

MemoryEventBus — zero dependencies
GraphUtils — zero dependencies, pure functions
```

Every class that depends on MemoryGraph does so through constructor injection. No class depends on MemoryStore or any UI framework.

---

## 5 Public APIs

### MemoryRegistry

| Method | Signature | Description |
|--------|-----------|-------------|
| `registerNodeType` | `(def: NodeTypeDefinition) => this` | Register a node type (idempotent) |
| `registerEdgeType` | `(def: EdgeTypeDefinition) => this` | Register an edge type (idempotent) |
| `registerProvider` | `(provider: MemoryProvider) => this` | Register a memory provider (idempotent) |
| `getProvider` | `(name: string) => MemoryProvider \| undefined` | Get provider by name |
| `getProviders` | `() => readonly MemoryProvider[]` | List all providers |
| `initialize` | `() => void` | Call `registerTypes()` on all providers (idempotent) |
| `isInitialized` | `() => boolean` | Check if initialized |
| `validateAll` | `() => readonly string[]` | Collect errors from all providers |
| `validateNodeType` | `(type: string) => boolean` | Check node type + its edge types exist |
| `canConnect` | `(source: NodeId, edgeType: string, target: NodeId) => boolean` | Check edge type allows source→target |
| `count` | `() => { nodeTypes, edgeTypes, providers }` | Count registrations |
| `reset` | `() => void` | Clear all registrations and providers |

### NodeTypeRegistry

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(def: NodeTypeDefinition) => this` | Register (idempotent, no overwrite) |
| `registerMany` | `(defs: NodeTypeDefinition[]) => this` | Batch register |
| `get` | `(name: string) => NodeTypeDefinition \| undefined` | Get definition |
| `has` | `(name: string) => boolean` | Check exists |
| `getAll` | `() => readonly NodeTypeDefinition[]` | List all |
| `getBySuperType` | `(superType: NodeSuperType) => readonly NodeTypeDefinition[]` | Filter by super type |
| `getAllowedEdgeTypes` | `(nodeType: string) => readonly string[]` | Allowed edges for node type |
| `isValidNodeType` | `(nodeType: string) => boolean` | Check type is registered |
| `isAllowedEdgeType` | `(nodeType: string, edgeType: string) => boolean` | Check edge is allowed for type |
| `validateNodeId` | `(nodeId: NodeId) => boolean` | Check nodeId.type is registered |
| `getDefaultMetadata` | `(nodeType: string) => Record<string, unknown>` | Clone of default metadata |
| `count` | `() => number` | Type count |
| `clear` | `() => void` | Remove all |

### EdgeTypeRegistry

| Method | Signature | Description |
|--------|-----------|-------------|
| `register` | `(def: EdgeTypeDefinition) => this` | Register (idempotent, no overwrite) |
| `registerMany` | `(defs: EdgeTypeDefinition[]) => this` | Batch register |
| `get` | `(name: string) => EdgeTypeDefinition \| undefined` | Get definition |
| `has` | `(name: string) => boolean` | Check exists |
| `getAll` | `() => readonly EdgeTypeDefinition[]` | List all |
| `canConnect` | `(sourceType, edgeType, targetType) => boolean` | Check source→edge→target |
| `getAllowedSourceTypes` | `(edgeType: string) => readonly string[]` | Allowed source types |
| `getAllowedTargetTypes` | `(edgeType: string) => readonly string[]` | Allowed target types |
| `isDirectional` | `(edgeType: string) => boolean` | Default true |
| `getDefaultMetadata` | `(edgeType: string) => Record<string, unknown>` | Clone of default metadata |
| `count` | `() => number` | Type count |
| `clear` | `() => void` | Remove all |

### MemoryGraph

| Method | Signature | Description |
|--------|-----------|-------------|
| `addNode` | `(input: NodeInput) => MemoryNode` | Create node, auto-generate ID |
| `updateNode` | `(id: NodeId, partial: Partial<MemoryNode>) => MemoryNode \| undefined` | Merge partial into node |
| `deleteNode` | `(id: NodeId) => boolean` | Remove node + all incident edges |
| `getNode` | `(id: NodeId) => MemoryNode \| undefined` | Get by ID (touches accessCount) |
| `getNodeById` | `(id: NodeId) => MemoryNode \| undefined` | Get by ID (no touch) |
| `hasNode` | `(id: NodeId) => boolean` | Existence check |
| `getAllNodes` | `() => readonly MemoryNode[]` | All nodes |
| `getNodesByType` | `(type: string) => readonly MemoryNode[]` | By type |
| `getNodesBySuperType` | `(superType: NodeSuperType) => readonly MemoryNode[]` | By super type prefix |
| `archiveNode` | `(id: NodeId) => MemoryNode \| undefined` | Set archived + status=archived |
| `restoreNode` | `(id: NodeId) => MemoryNode \| undefined` | Set active |
| `addEdge` | `(input: EdgeInput) => MemoryEdge \| undefined` | Create edge (undefined if nodes missing) |
| `deleteEdge` | `(id: EdgeId) => boolean` | Remove edge |
| `getEdge` | `(id: EdgeId) => MemoryEdge \| undefined` | Get by ID |
| `getEdgesByNode` | `(id: NodeId) => readonly MemoryEdge[]` | All edges incident to node |
| `getOutgoingEdges` | `(id: NodeId) => readonly MemoryEdge[]` | Edges where node is source |
| `getIncomingEdges` | `(id: NodeId) => readonly MemoryEdge[]` | Edges where node is target |
| `getOutgoingNeighbors` | `(id: NodeId) => readonly MemoryNode[]` | Direct successors |
| `getIncomingNeighbors` | `(id: NodeId) => readonly MemoryNode[]` | Direct predecessors |
| `getNeighbors` | `(id: NodeId) => readonly MemoryNode[]` | All adjacent (deduped) |
| `getConnectedEdges` | `(id: NodeId) => { outgoing, incoming }` | Both edge directions |
| `nodeCount` | `() => number` | Node count |
| `edgeCount` | `() => number` | Edge count |
| `snapshot` | `() => MemorySnapshot` | Deep copy of all nodes + edges |
| `loadSnapshot` | `(snapshot: MemorySnapshot) => void` | Replace entire graph state |
| `clear` | `() => void` | Remove all nodes and edges |
| `stats` | `() => MemoryGraphStats` | Aggregated counts |
| `onNodeChange` | `(listener) => Unsubscribe` | Subscribe to node mutations |
| `onEdgeChange` | `(listener) => Unsubscribe` | Subscribe to edge mutations |

### RelationshipEngine

| Method | Signature | Description |
|--------|-----------|-------------|
| `canAddEdge` | `(input: EdgeInput) => { valid, errors }` | Validate without mutating |
| `addEdge` | `(input: EdgeInput) => MemoryEdge \| undefined` | Validate + add (atomic) |
| `deleteNodeWithEdges` | `(id: NodeId) => boolean` | Delete all incident edges + node |
| `getConnectedComponent` | `(id: NodeId) => { nodes, edges }` | Full connected subgraph |
| `validateGraph` | `() => readonly ValidationError[]` | Full graph validation |
| `findCycles` | `() => readonly CircularDependency[]` | Detect all directed cycles |
| `wouldCreateCycle` | `(sourceId, targetId) => CircularDependency \| undefined` | Check edge would create cycle |
| `getRelationshipSummary` | `(id: NodeId) => { node, outgoingCount, incomingCount, totalConnections, connectedTypes }` | Relationship stats |

### GraphTraversal

| Method | Signature | Description |
|--------|-----------|-------------|
| `bfs` | `(startId, { maxDepth?, edgeTypes? }) => TraversalResult` | Breadth-first search |
| `dfs` | `(startId, { maxDepth?, edgeTypes? }) => TraversalResult` | Depth-first search |
| `findPaths` | `(startId, endId, { maxDepth?, edgeTypes? }) => TraversalResult[]` | All paths between two nodes |
| `findShortestPath` | `(startId, endId, { edgeTypes? }) => TraversalResult \| undefined` | Shortest path (fewest edges) |
| `getConnectedComponent` | `(startId) => TraversalResult` | All reachable nodes |
| `getNeighborsAtDepth` | `(id, depth, { edgeTypes?, direction? }) => readonly MemoryNode[]` | Nodes at exact distance |

### QueryEngine

| Method | Signature | Description |
|--------|-----------|-------------|
| `execute` | `(query: SearchQuery) => SearchResult` | Full query pipeline |
| `findAll` | `(options?: QueryOptions) => SearchResult` | All nodes with sort/pagination |
| `findByType` | `(type: string, options?: QueryOptions) => SearchResult` | By exact type |
| `findBySuperType` | `(superType: string, options?: QueryOptions) => SearchResult` | By super type prefix |
| `findByTag` | `(tag: string, options?: QueryOptions) => SearchResult` | By single tag |
| `findBySource` | `(source: string, options?: QueryOptions) => SearchResult` | By source |
| `searchByKeyword` | `(keyword: string, options?: QueryOptions) => SearchResult` | Text search (returns empty for blank) |

### MemoryEventBus

| Method | Signature | Description |
|--------|-----------|-------------|
| `emit` | `(event: MemoryEvent) => void` | Publish event |
| `on` | `(eventType: string, handler: EventHandler) => Unsubscribe` | Subscribe to specific type |
| `onAny` | `(handler: EventHandler) => Unsubscribe` | Subscribe to all events |
| `once` | `(eventType: string, handler: EventHandler) => Unsubscribe` | Subscribe for one event |
| `subscribe` | `(subscriber: Subscriber) => Unsubscribe` | Subscribe with optional filter |
| `off` | `(eventType: string, handler: EventHandler) => void` | Unsubscribe by type+handler |
| `getHistory` | `(eventType?: string) => readonly MemoryEvent[]` | Event history (ring buffer) |
| `clearHistory` | `() => void` | Clear history |
| `removeAllListeners` | `(eventType?: string) => void` | Remove listeners (optional type) |
| `listenerCount` | `(eventType?: string) => number` | Count subscribers |

### MemorySelectors

| Method | Signature | Description |
|--------|-----------|-------------|
| `getRecentNodes` | `(count = 10) => readonly MemoryNode[]` | Most recently updated |
| `getMostAccessedNodes` | `(count = 10) => readonly MemoryNode[]` | Highest accessCount |
| `getMostImportantNodes` | `(count = 10) => readonly MemoryNode[]` | Highest importance (excludes archived) |
| `getHighestConfidenceNodes` | `(count = 10) => readonly MemoryNode[]` | Highest confidence (excludes archived) |
| `getPinnedNodes` | `() => readonly MemoryNode[]` | Pinned + not archived |
| `getArchivedNodes` | `() => readonly MemoryNode[]` | All archived |
| `getActiveNodes` | `() => readonly MemoryNode[]` | Not archived + status=active |
| `getActionNodes` | shorthand for super type "action" |
| `getObservationNodes` | shorthand for super type "observation" |
| `getKnowledgeNodes` | shorthand for super type "knowledge" |
| `getArtifactNodes` | shorthand for super type "artifact" |
| `getEntityNodes` | shorthand for super type "entity" |
| `getMetaNodes` | shorthand for super type "meta" |
| `getNodesWithTag` | `(tag: string) => readonly MemoryNode[]` | Single tag (excludes archived) |
| `getNodesWithTags` | `(tags, mode) => readonly MemoryNode[]` | Multi-tag (all/any) |
| `getNodesFromSource` | `(source: string) => readonly MemoryNode[]` | By source (excludes archived) |
| `getNodesByStatus` | `(status: NodeStatus) => readonly MemoryNode[]` | By status |
| `getEdgesForNode` | `(id: NodeId) => readonly MemoryEdge[]` | All edges for node |
| `getConnectedNodes` | `(id: NodeId) => readonly MemoryNode[]` | All neighbors |
| `getOutgoingConnections` | `(id: NodeId) => readonly MemoryNode[]` | Outgoing neighbors |
| `getIncomingConnections` | `(id: NodeId) => readonly MemoryNode[]` | Incoming neighbors |
| `search` | `(keyword: string) => readonly MemoryNode[]` | Text search (title/summary/tags/type/subtype) |
| `findDuplicates` | `(predicate) => readonly [MemoryNode, MemoryNode][]` | Custom duplicate detection |
| `getStats` | `() => { total, active, archived, pinned, bySuperType }` | Aggregated stats |

### MemoryStore

| Method | Signature | Description |
|--------|-----------|-------------|
| `addNode` | `(input: NodeInput) => MemoryNode` | Delegates to graph |
| `updateNode` | `(id, partial) => MemoryNode \| undefined` | Delegates to graph |
| `deleteNode` | `(id: NodeId) => boolean` | Delegates to RelationshipEngine (cascade edges) |
| `getNode` | `(id: NodeId) => MemoryNode \| undefined` | Delegates to graph |
| `addEdge` | `(input: EdgeInput) => MemoryEdge \| undefined` | Delegates to RelationshipEngine (validated) |
| `deleteEdge` | `(id: EdgeId) => boolean` | Delegates to graph |
| `search` | `(query: SearchQuery) => SearchResult` | Delegates to QueryEngine |
| `snapshot` | `() => MemorySnapshot` | Delegates to graph |
| `loadSnapshot` | `(snapshot: MemorySnapshot) => void` | Delegates to graph + refresh |
| `clear` | `() => void` | Clear graph + emit graph:cleared |
| `onNodeEvent` | `(eventType, handler) => Unsubscribe` | Typed node event subscription |
| `onEdgeEvent` | `(eventType, handler) => Unsubscribe` | Typed edge event subscription |
| `onAnyEvent` | `(handler) => Unsubscribe` | All events |
| `subscribe` | `(listener: () => void) => Unsubscribe` | State change subscription (for React) |
| `getState` | `() => MemoryStoreState` | { nodeCount, edgeCount, lastEvent } |
| `getStats` | `() => SelectorStats` | Delegates to selectors |

### Singleton Accessors

```
getMemoryRegistry() → MemoryRegistry
setMemoryRegistry(registry) → void
resetMemoryRegistry() → void

getMemoryStore() → MemoryStore
setMemoryStore(store) → void
resetMemoryStore() → void
```

---

## 6 Node Model

### Core Type: `MemoryNode<TMetadata>`

```
NodeId { value: string, type: string }
  - value: unique identifier (auto-generated as "{type}_{timestamp}_{counter}" or caller-provided)
  - type: must match a registered NodeTypeDefinition.name

Properties (all readonly):
  - type: string                          — exact type, matches registered NodeTypeDefinition.name
  - subtype: string                       — free-form subcategory
  - title: string                         — human-readable label
  - summary: string                       — brief description
  - source: string                        — origin identifier (e.g., "chat", "vision", "voice")
  - tags: readonly string[]               — free-form labels
  - importance: number [0..10]            — 1 default, higher = more important
  - confidence: number [0..1]             — 1 default, higher = more certain
  - accessCount: number                   — incremented on every getNode() call
  - pinned: boolean                       — true if user pinned
  - archived: boolean                     — true if archived
  - verified: boolean                     — true if human-verified
  - verificationMethod: string            — how verification occurred
  - status: "active" | "archived" | "deleted"
  - createdAt: number                     — epoch ms
  - updatedAt: number                     — epoch ms (bumped on every mutation)
  - lastAccessed: number                  — epoch ms (bumped on getNode)
  - metadata: TMetadata                   — extensible payload (defaults to Record<string, unknown>)
```

### NodeInput (creation contract)

```
id?: string                 — skip for auto-generation
type: string                — required, must be registered
subtype: string             — required
title: string               — required, non-empty
source: string              — required, non-empty
summary?: string
metadata?: TMetadata
tags?: string[]
importance?: number          — default 1
confidence?: number          — default 1
pinned?: boolean             — default false
archived?: boolean           — default false
verified?: boolean           — default false
verificationMethod?: string  — default ""
createdAt?: number           — default Date.now()
status?: NodeStatus          — default "active"
```

### Node Lifecycle

```
Created → Active (status = "active")
Active → Archived (archiveNode)
Archived → Active (restoreNode)
Any → Deleted (deleteNode removes permanently, with all incident edges)
```

### NodeSuperType Hierarchy

All node types belong to one of six super types derived by prefix:

| SuperType | Prefix | Purpose |
|-----------|--------|---------|
| `action` | `action:*` | Executions, commands, workflows |
| `observation` | `observation:*` | Captures, screenshots, sensor readings |
| `knowledge` | `knowledge:*` | Facts, summaries, extracted entities |
| `artifact` | `artifact:*` | Generated files, outputs |
| `entity` | `entity:*` | People, organizations, locations |
| `meta` | `meta:*` | Tags, collections, preferences |

---

## 7 Edge Model

### Core Type: `MemoryEdge<TMetadata>`

```
EdgeId { value: string }
  - value: unique identifier (auto-generated as "edge_{timestamp}_{counter}" or caller-provided)

Properties (all readonly):
  - sourceNodeId: NodeId     — must reference existing node
  - targetNodeId: NodeId     — must reference existing node
  - type: string             — must match registered EdgeTypeDefinition.name
  - strength: number [0..1]  — 1 default
  - weight: number [0..1]    — 1 default
  - metadata: TMetadata      — extensible payload
  - createdAt: number         — epoch ms
```

### EdgeInput (creation contract)

```
id?: string
sourceNodeId: NodeId     — required
targetNodeId: NodeId     — required
type: string             — required, must be registered
strength?: number        — default 1
weight?: number          — default 1
metadata?: TMetadata
```

### Edge Validation Rules

- Both source and target nodes must exist in the graph
- Edge type must be registered
- `canConnect(sourceNode.type, edgeType, targetNode.type)` must pass
- `strength` must be [0, 1]
- `weight` must be [0, 1]
- Must not create a directed cycle (optional, enforced by RelationshipEngine)

---

## 8 Registry Model

### NodeTypeDefinition

```
name: string                — unique identifier (e.g., "knowledge:statement")
superType: NodeSuperType    — one of the six super types
description: string         — human-readable
allowedEdgeTypes: string[]  — which edge types this node can emit
allowedAsTargetFor: string[] — which edge types can target this node
defaultMetadata: Record     — default metadata values for new nodes
```

### EdgeTypeDefinition

```
name: string                — unique identifier (e.g., "produces")
description: string         — human-readable
allowedSourceTypes: string[] — which node types can be the source
allowedTargetTypes: string[] — which node types can be the target
directional: boolean        — true = directed edge, false = undirected
defaultMetadata: Record     — default metadata values for new edges
```

### Registration Rules

- `register` is idempotent: calling twice with the same name does not overwrite
- `registerMany` batches individual `register` calls
- `validateNodeType` checks every `allowedEdgeType` has a corresponding EdgeTypeDefinition
- `reset()` clears all types and providers
- A type is fully validated only when all its referenced edge types also exist

### Singleton Policy

`MemoryRegistry` has a module-level singleton (`getMemoryRegistry()`) but is NOT required. Any caller can instantiate their own `new MemoryRegistry()`. The singleton is a convenience for the default application context.

---

## 9 Query Model

### SearchQuery

```
keyword?: string            — fuzzy text search (title/summary/tags/type/subtype)
filters?: SearchFilters     — structured field filters
relationship?: {
  seedNodeId: NodeId
  filter: RelationshipFilter
}
options: QueryOptions       — sort, pagination
```

### Query Pipeline (execute)

```
Input: SearchQuery
  1. Parse (normalize defaults via QueryParser)
  2. Keyword filter   — if keyword present, apply text match
  3. Field filters    — types, superTypes, tags, statuses, sources, dates, importance, confidence, pinned, archived
  4. Traversal filter — if relationship provided, intersect with BFS result
  5. Sort             — by field + direction
  6. Paginate         — offset + limit
Output: SearchResult { nodes, total, hasMore, query }
```

### SearchFilters

```
types?: string[]             — exact type match
superTypes?: NodeSuperType[] — prefix match
tags?: string[]              — any-of match
statuses?: NodeStatus[]      — status match
sources?: string[]           — source match
dateFrom?: number            — createdAt >=
dateTo?: number              — createdAt <=
importanceMin?: number       — importance >=
importanceMax?: number       — importance <=
confidenceMin?: number       — confidence >=
confidenceMax?: number       — confidence <=
pinned?: boolean
archived?: boolean
```

### Sortable Fields

```
"createdAt" | "updatedAt" | "lastAccessed" | "importance" | "confidence" | "accessCount" | "title"
```

### Invariant

Queries never mutate graph state. The `execute` method copies all nodes defensively before filtering. `getNode` mutates `lastAccessed`/`accessCount` (intentional side effect) but query methods use `getNodeById` which does not.

---

## 10 Event Model

### Event Types

| Type | Payload | Fires When |
|------|---------|------------|
| `node:created` | NodeChange | addNode |
| `node:updated` | NodeChange | updateNode |
| `node:deleted` | NodeChange | deleteNode |
| `node:archived` | NodeChange | archiveNode |
| `node:restored` | NodeChange | restoreNode |
| `edge:created` | EdgeChange | addEdge |
| `edge:deleted` | EdgeChange | deleteEdge |
| `relationship:changed` | { nodeId, timestamp } | (reserved for future use) |
| `graph:cleared` | { timestamp } | store.clear |

### NodeChange

```
type: "created" | "updated" | "deleted" | "archived" | "restored"
node: MemoryNode
previous?: MemoryNode    — present on "updated"
timestamp: number
```

### EdgeChange

```
type: "created" | "deleted"
edge: MemoryEdge
timestamp: number
```

### Event Invariants

- Events are immutable objects (all properties `readonly`)
- The same event object is passed to all subscribers
- The event bus is synchronous (subscribers are called during `emit`)
- History is a ring buffer (default capacity 1000 events)
- Wildcard subscribers (`onAny`) receive every event
- Filtered subscribers (`subscribe` with `filter`) receive matching events only
- `once` auto-unsubscribes after first event

---

## 11 Validation Rules

### Node Validation (validateNode)

| Code | Condition |
|------|-----------|
| `INVALID_NODE_ID` | id.value or id.type is empty |
| `MISSING_TYPE` | type is empty |
| `UNKNOWN_NODE_TYPE` | type is not registered |
| `MISSING_TITLE` | title is empty |
| `MISSING_SOURCE` | source is empty |
| `INVALID_IMPORTANCE` | importance outside [0, 10] |
| `INVALID_CONFIDENCE` | confidence outside [0, 1] |
| `FUTURE_CREATED_AT` | createdAt > Date.now() + 1s |
| `INVALID_TIMESTAMP` | updatedAt < createdAt - 1s |
| `ARCHIVED_AND_PINNED` | both archived and pinned are true |

### Edge Validation (validateEdge)

| Code | Condition |
|------|-----------|
| `INVALID_EDGE_ID` | id.value is empty |
| `MISSING_EDGE_TYPE` | type is empty |
| `UNKNOWN_EDGE_TYPE` | type is not registered |
| `INVALID_SOURCE_NODE` | sourceNodeId is missing |
| `INVALID_TARGET_NODE` | targetNodeId is missing |
| `INVALID_STRENGTH` | strength outside [0, 1] |
| `INVALID_WEIGHT` | weight outside [0, 1] |

### Edge Connection Validation (canAddEdge)

| Code | Condition |
|------|-----------|
| `SOURCE_NODE_NOT_FOUND` | source node does not exist |
| `TARGET_NODE_NOT_FOUND` | target node does not exist |
| `UNKNOWN_EDGE_TYPE` | edge type not registered |
| `INVALID_EDGE_CONNECTION` | source/target types incompatible |
| `INVALID_STRENGTH` | strength outside [0, 1] |
| `INVALID_WEIGHT` | weight outside [0, 1] |
| `CIRCULAR_DEPENDENCY` | adding edge would create a cycle |

### Graph Validation (validateGraph)

| Code | Condition |
|------|-----------|
| `INVALID_NODE_TYPE` | node's type not registered |
| `CIRCULAR_DEPENDENCY` | directed cycle exists |

---

## 12 Ownership Model

- **MemoryRegistry** owns type metadata (NodeTypeRegistry + EdgeTypeRegistry)
- **MemoryGraph** owns in-memory state (nodes, edges, adjacency)
- **MemoryEventBus** owns subscriber list + event history
- **MemoryStore** owns the composition: graph + registry + events + selectors + query
- **QueryEngine** is stateless (reads from graph, never writes)
- **RelationshipEngine** is stateless (reads registry + graph, writes through graph)
- **GraphTraversal** is stateless (reads from graph only)
- **MemoryValidation** is stateless (reads registries only)
- **MemorySelectors** is stateless (reads from graph only)
- **GraphUtils** is pure functions (zero state)

No subsystem owns another subsystem's state. Ownership is exclusive and explicit.

---

## 13 Extension Model

### Provider Contract

```
interface MemoryProvider {
  name: string                    — unique provider identifier
  registerTypes: () => void      — called during MemoryRegistry.initialize()
  canHandleNode: (node) => boolean
  canHandleEdge: (edge) => boolean
  validate: () => string[]       — return error messages, empty = valid
}
```

Providers are registered via `MemoryRegistry.registerProvider()`. During `initialize()`, each provider's `registerTypes()` is called exactly once. Providers can register additional `NodeTypeDefinition` and `EdgeTypeDefinition` entries.

### Adding a Node Type

```typescript
registry.registerNodeType({
  name: "knowledge:statement",
  superType: "knowledge",
  description: "A factual knowledge statement",
  allowedEdgeTypes: ["references", "derives_from"],
  allowedAsTargetFor: ["references"],
  defaultMetadata: { confidence: 0.5 },
})
```

### Adding an Edge Type

```typescript
registry.registerEdgeType({
  name: "derives_from",
  description: "Indicates derivation from another node",
  allowedSourceTypes: ["knowledge:statement"],
  allowedTargetTypes: ["knowledge:statement"],
  directional: true,
  defaultMetadata: {},
})
```

### NodeTypeConstants / EdgeTypeConstants

The `types.ts` file defines string constant objects (`NodeTypeConstants`, `EdgeTypeConstants`) with pre-defined type names. These are conventions, not enforced — any string can be used as long as the type is registered.

---

## 14 Provider Contract

A MemoryProvider is the extension boundary for domain modules (chat, vision, voice, execution, browser) to contribute their type definitions to the Memory Core.

### Contract

```
registerTypes()
  Called once during MemoryRegistry.initialize().
  Use registry.registerNodeType() and registry.registerEdgeType()
  to define the types this provider owns.

canHandleNode(node: MemoryNode): boolean
  Return true if this provider should handle serialization or
  processing of the given node.

canHandleEdge(edge: MemoryEdge): boolean
  Return true if this provider should handle the given edge.

validate(): readonly string[]
  Return validation errors for this provider's type configuration.
  Empty array = valid.
```

### Usage Pattern

```typescript
const chatProvider: MemoryProvider = {
  name: "chat",
  registerTypes() {
    registry.registerNodeType(conversationNodeType)
    registry.registerEdgeType(conversationEdgeType)
  },
  canHandleNode: (node) => node.type === "conversation",
  canHandleEdge: () => false,
  validate: () => [],
}

registry.registerProvider(chatProvider)
registry.initialize()
```

---

## 15 Invariants

1. **MemoryGraph never depends on UI.** It imports zero React, DOM, or browser APIs. It is pure TypeScript with `Map` and `Set`.

2. **MemoryStore is framework agnostic.** Its `subscribe`/`getState` pattern is compatible with `useSyncExternalStore` but imports nothing from React.

3. **Registries own type metadata exclusively.** Only `NodeTypeRegistry` and `EdgeTypeRegistry` can answer "is this type valid?" or "what edges are allowed?"

4. **Queries never mutate state.** `QueryEngine.execute` copies all nodes before filtering. `RelationshipEngine.canAddEdge` does not add the edge.

5. **Events are immutable.** Every property on `MemoryEvent`, `NodeChange`, and `EdgeChange` is `readonly`.

6. **Nodes are immutable after creation.** Property changes produce a new object via spread in `updateNode`, `archiveNode`, `restoreNode`. The old object is never mutated.

7. **Edges are immutable after creation.** Edge properties are set once in `addEdge` and never mutated.

8. **Only registries register types.** `MemoryRegistry.registerNodeType` and `registerEdgeType` are the sole entry points for type registration. Providers access them through the registry.

9. **Graph adjacency is dual-indexed.** Every edge updates both `adjacencyOut[source]` and `adjacencyIn[target]`. Deleting an edge cleans both.

10. **Node deletion cascades edges.** `deleteNode` removes all incident edges before removing the node. The caller does not need to manually delete edges first.

11. **MemoryStore bridges Graph notifications to Events.** Graph's `onNodeChange`/`onEdgeChange` listeners emit corresponding `MemoryEventBus` events. External code subscribes to the event bus, not to graph listeners directly.

12. **Validation inputs are optional.** `MemoryValidation` validates in-memory `MemoryNode`/`MemoryEdge` objects as well as creation `NodeInput`/`EdgeInput` objects.

13. **Every node mutation updates `updatedAt`.** Even `archiveNode` and `restoreNode` bump the timestamp.

14. **`getNode` has a side effect.** It increments `accessCount` and updates `lastAccessed`. Use `getNodeById` to read without side effects.

15. **Empty/whitespace keyword in `SearchQuery` returns nothing.** When `keyword` is explicitly provided as `""` or `" "`, the query returns zero results. When `keyword` is `undefined`, no text filter is applied.

---

## 16 Performance Expectations

| Operation | Time Complexity | Notes |
|-----------|----------------|-------|
| addNode | O(1) | Map insertion + type index |
| getNode | O(1) | Map lookup (with accessCount bump) |
| updateNode | O(1) | Map update |
| deleteNode | O(E) | Must remove all incident edges |
| addEdge | O(1) | Map insertion + adjacency update |
| deleteEdge | O(1) | Map deletion + adjacency cleanup |
| getNeighbors | O(degree) | Adjacency lookup + Map.get |
| getAllNodes | O(N) | Spread of Map.values() |
| snapshot | O(N + E) | Deep copy of all nodes + edges |
| loadSnapshot | O(N + E) | Rebuild indices |
| BFS/DFS | O(N + E) | Visits each node/edge once |
| findPaths | O(b^d) | Exponential in worst case (unconstrained) |
| findCycles | O(N + E) | DFS-based |
| execute (no keyword) | O(N) | Linear scan + filters |
| execute (with keyword) | O(N) | Linear scan + string matching |
| MemoryValidation.validateNode | O(1) | Fixed checks |
| MemoryValidation.validateGraph | O(N + E) | All nodes + cycle detection |

N = node count, E = edge count, d = depth, b = branching factor

### Memory

Each node and edge is a plain object stored in `Map<string, MemoryNode>` / `Map<string, MemoryEdge>`. Adjacency is stored as `Map<string, Set<string>>` where each set entry is a string key reference. The total memory footprint is proportional to N + E with no fixed-size buffers or pooled objects.

### History

The event history is a ring buffer with default capacity 1000. Each entry retains a reference to the event object. Long-lived references to large payloads prevent garbage collection. Call `clearHistory()` or configure a lower `maxHistory` if this is a concern.

---

## 17 Thread Safety

The Memory Core runs in a single-threaded JavaScript environment. There are no locks, mutexes, or atomic operations. In the browser or Node.js main thread, synchronous operations are naturally safe.

**When migrating to Web Workers or shared memory:**
- Each `MemoryStore` instance is single-threaded by design
- Snapshots (`snapshot()`) provide serializable state for cross-thread transfer
- Post-message communication should be used instead of shared references
- The event bus is not thread-safe; consumers in different threads must use their own instance or communicate via messages

---

## 18 Versioning Policy

- The Memory Core version (1.0.0) is declared in `constants.ts` as `MEMORY_VERSION`
- Major version bump = breaking change to any public API
- Minor version bump = backward-compatible addition
- Patch version bump = internal bug fix with no API change
- All public classes, methods, and types defined in `index.ts` are versioned
- Private/internal methods (prefixed with `private` in TypeScript) are not versioned
- The event bus history format is not versioned (always reflects the current event types)

---

## 19 Breaking Change Policy

The following constitute breaking changes:

- Renaming or removing any public class, method, or type
- Adding required parameters to a public method
- Changing return types
- Removing event types or changing payload shape
- Changing `NodeInput` or `EdgeInput` required fields
- Changing validation rules that would reject previously valid data
- Changing default values that alter behavior

The following do NOT constitute breaking changes:

- Adding new public methods or types
- Adding new event types
- Adding optional parameters
- Adding new validation rules
- Adding new selectors
- Changing internal implementation while preserving behavior

Breaking changes require a major version bump and migration guide.

---

## 20 Migration Rules

When upgrading between versions:

1. **Same major version:** Drop-in replacement. No code changes required.
2. **Major version bump:** 
   - Compare the previous ADR-008 with the new one
   - Update any imports or method calls that changed
   - Re-register any custom node/edge types if the registry API changed
   - Migrate snapshot format if `MemorySnapshot` shape changed
   - Run the full test suite after upgrading
3. **Custom providers** must be updated if `MemoryProvider` interface changes
4. **Event consumers** must be updated if event type strings or payload shapes change
5. **Serialized data** (snapshots) should be migrated via adapter function before calling `loadSnapshot`

Migration is always: old code → adapt → new API. Backward compatibility shims should live in the consumer, not in the Memory Core.
