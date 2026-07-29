# EVE OS — API Contracts v1.0

**Document:** 04_API_Contracts.md
**Status:** Living
**Purpose:** Document every public API contract in Eve OS across frontend and backend.

---

# Table of Contents

1. [Conversation APIs](#1-conversation-apis)
2. [Execution APIs](#2-execution-apis)
3. [Memory APIs](#3-memory-apis)
4. [Registry APIs](#4-registry-apis)
5. [Command APIs](#5-command-apis)
6. [Workspace APIs](#6-workspace-apis)
7. [Plugin APIs](#7-plugin-apis)
8. [Capability APIs](#8-capability-apis)
9. [Store APIs](#9-store-apis)
10. [Event APIs](#10-event-apis)
11. [Provider APIs](#11-provider-apis)

---

## 1. Conversation APIs

### 1.1 `IConversationRepository` (Backend — Python)

**Purpose:** Abstract data access for conversations and messages.
**Owner:** Backend Conversation Module
**File:** `src/backend/aios/conversation/interfaces.py`
**Thread Safety:** Async-safe
**Versioning:** Backward-compatible method signatures

| Method | Parameters | Returns | Error Conditions |
|--------|-----------|---------|-----------------|
| `create_conversation` | `conversation: Conversation` | `Conversation` | DB write failure |
| `get_conversation` | `conversation_id: str` | `Conversation \| None` | Not found |
| `list_conversations` | `limit: int = 50, offset: int = 0` | `list[Conversation]` | — |
| `update_conversation` | `conversation: Conversation` | `Conversation` | Not found |
| `delete_conversation` | `conversation_id: str` | `None` | Not found |
| `add_message` | `message: Message` | `Message` | Conversation not found |
| `get_messages` | `conversation_id: str, limit: int = 100, offset: int = 0` | `list[Message]` | — |
| `clear_history` | `conversation_id: str` | `None` | Not found |

### 1.2 `IConversationService` (Backend — Python)

**Purpose:** Business logic for conversation lifecycle and messaging.
**Owner:** Backend Conversation Module
**File:** `src/backend/aios/conversation/interfaces.py`
**Thread Safety:** Async-safe

| Method | Parameters | Returns | Error Conditions |
|--------|-----------|---------|-----------------|
| `create_conversation` | `title: str \| None, project: str \| None` | `Conversation` | — |
| `get_conversation` | `conversation_id: str` | `Conversation` | Not found |
| `list_conversations` | `limit: int = 50, offset: int = 0` | `list[Conversation]` | — |
| `delete_conversation` | `conversation_id: str` | `None` | Not found |
| `rename_conversation` | `conversation_id: str, title: str` | `Conversation` | Not found |
| `send_message` | `conversation_id: str, content: str` | `Message` | Conversation not found |
| `stream_message` | `conversation_id: str, content: str` | `AsyncIterator[dict]` | Streaming error |
| `get_history` | `conversation_id: str, limit: int = 100, offset: int = 0` | `list[Message]` | — |
| `clear_history` | `conversation_id: str` | `None` | Not found |

### 1.3 Conversation Models

**File:** `src/backend/aios/conversation/models.py`

**`Conversation`**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `uuid4().hex` | Unique identifier |
| `title` | `str` | `""` | Display title |
| `created_at` | `datetime \| None` | `utcnow()` | Creation timestamp |
| `updated_at` | `datetime \| None` | `utcnow()` | Last update |
| `active_project` | `str \| None` | `None` | Linked project |
| `is_active` | `bool` | `True` | Conversation active |
| `mode` | `str` | `"chat"` | Operating mode |
| `metadata` | `dict` | `{}` | Extensible metadata |
| `message_count` | `int` | `0` | Running count |
| `parent_id` | `str \| None` | `None` | Fork parent |
| `branch_point_message_id` | `str \| None` | `None` | Fork point |

**`Message`**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `uuid4().hex` | Unique identifier |
| `conversation_id` | `str` | `""` | Parent conversation |
| `role` | `MessageRole` | `USER` | system/user/assistant/tool |
| `content` | `str` | `""` | Message body |
| `timestamp` | `datetime \| None` | `utcnow()` | Creation time |
| `attachments` | `list[dict]` | `[]` | File/media attachments |
| `tool_calls` | `list[ToolCall]` | `[]` | Tools invoked |
| `tool_results` | `list[dict]` | `[]` | Tool outputs |
| `metadata` | `dict` | `{}` | Extensible metadata |
| `tokens_used` | `int` | `0` | Token count |
| `edit_history` | `list[EditEntry]` | `[]` | Edit trail |
| `is_regenerated` | `bool` | `False` | Regeneration flag |
| `latency_ms` | `float` | `0.0` | Response time |
| `planning_context` | `PlanningContext \| None` | `None` | Planner output |
| `execution_context` | `ExecutionContext \| None` | `None` | Execution state |

**`MessageRole`** enum: `SYSTEM`, `USER`, `ASSISTANT`, `TOOL`

**`StreamEventType`** enum: `TOKEN`, `DONE`, `ERROR`, `TOOL_CALL`, `TOOL_RESULT`, `STATUS`, `PLANNER_STARTED`, `PLANNER_COMPLETED`, `MEMORY_RETRIEVAL`, `TOOL_REQUESTED`, `TOOL_RUNNING`, `TOOL_COMPLETED`, `CONTEXT_LOADED`, `FINAL_RESPONSE`, `TITLE_GENERATED`, `ANALYTICS`, `VISION_OBSERVATION`

**`ToolCall`**
| Field | Type | Description |
|-------|------|-------------|
| `tool_name` | `str` | Tool identifier |
| `capability` | `str` | Capability identifier |
| `parameters` | `dict` | Input params |
| `result` | `Any` | Output |
| `execution_time` | `float` | Duration in ms |
| `status` | `ToolCallStatus` | pending/running/success/failed/cancelled |

### 1.4 REST API Routes (Backend)

**File:** `src/backend/aios/api/chat.py`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/chat/conversation` | Create conversation |
| `POST` | `/chat/message` | Send message |
| `POST` | `/chat/stream` | Stream message response |
| `GET` | `/chat/history/{id}` | Get conversation history |
| `DELETE` | `/chat/conversation/{id}` | Delete conversation |

### 1.5 Frontend API Client

**File:** `src/frontend/src/services/api.ts`

```typescript
api.chat.send(content: string, conversationId?: string): Promise<Response>
api.chat.history(conversationId: string): Promise<Response>
api.chat.createConversation(title?: string): Promise<Response>
api.chat.deleteConversation(id: string): Promise<Response>
```

**Events Published:** `conversation.created`, `conversation.deleted`, `message.sent`
**Extension Rules:** New message roles must extend `MessageRole` enum. New stream events add to `StreamEventType`.
**Future Compatibility:** Service interface supports alternative storage backends via `IConversationRepository`.

---

## 2. Execution APIs

### 2.1 `IExecutionEngine` (Backend — Python)

**Purpose:** Lifecycle management for execution sessions.
**Owner:** Backend Execution Engine
**File:** `src/backend/aios/execution/interfaces.py`
**Thread Safety:** Async-safe

| Method | Parameters | Returns | Error Conditions |
|--------|-----------|---------|-----------------|
| `start_execution` | `objective: str, conversation_id: str, owner: str, priority: int` | `Execution` | Planner failure |
| `get_execution` | `execution_id: str` | `Execution` | Not found |
| `pause_execution` | `execution_id: str` | `Execution` | Not running |
| `resume_execution` | `execution_id: str` | `Execution` | Not paused |
| `cancel_execution` | `execution_id: str` | `Execution` | Already terminal |
| `get_execution_progress` | `execution_id: str` | `ExecutionProgress` | Not found |
| `stream_events` | `execution_id: str` | `AsyncIterator[dict]` | Not found |

### 2.2 `IExecutor` (Backend — Python)

| Method | Parameters | Returns | Error Conditions |
|--------|-----------|---------|-----------------|
| `execute_task` | `task: Task` | `Task` | Execution failure |
| `validate_task` | `task: Task` | `bool` | — |

### 2.3 `IScheduler` (Backend — Python)

| Method | Parameters | Returns | Error Conditions |
|--------|-----------|---------|-----------------|
| `schedule` | `execution: Execution, tasks: list[Task]` | `AsyncIterator[Task]` | — |
| `cancel` | `execution_id: str` | `None` | Not found |
| `pause` | `execution_id: str` | `None` | Not found |
| `resume` | `execution_id: str` | `None` | Not found |

### 2.4 `IRecoveryEngine` (Backend — Python)

| Method | Parameters | Returns | Error Conditions |
|--------|-----------|---------|-----------------|
| `handle_failure` | `execution: Execution, task: Task` | `tuple[bool, Task \| None]` | — |
| `can_continue` | `execution: Execution` | `bool` | — |

### 2.5 Execution Models

**File:** `src/backend/aios/execution/models.py`

**`Execution`**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `uuid4().hex` | Unique ID |
| `status` | `ExecutionStatus` | `PENDING` | Current status |
| `objective` | `str` | `""` | Goal description |
| `created_at` | `datetime` | `utcnow()` | Created |
| `updated_at` | `datetime` | `utcnow()` | Updated |
| `started_at` | `datetime \| None` | `None` | Started |
| `completed_at` | `datetime \| None` | `None` | Completed |
| `owner` | `str` | `""` | Owner ID |
| `priority` | `Priority` | `NORMAL` | Priority level |
| `metadata` | `dict` | `{}` | Extensible |
| `plan_id` | `str` | `""` | Plan reference |
| `conversation_id` | `str` | `""` | Parent conversation |

**`ExecutionStatus`** enum: `PENDING`, `PLANNING`, `WAITING_FOR_PERMISSION`, `READY`, `RUNNING`, `WAITING`, `RETRYING`, `PAUSED`, `CANCELLED`, `COMPLETED`, `FAILED`

**`Task`**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | `uuid4().hex` | Unique ID |
| `execution_id` | `str` | `""` | Parent execution |
| `parent_task` | `str \| None` | `None` | Dependency chain |
| `capability` | `str` | `""` | Capability to use |
| `tool` | `str` | `""` | Tool to execute |
| `parameters` | `dict` | `{}` | Input params |
| `dependencies` | `list[str]` | `[]` | Task deps |
| `retries` | `int` | `0` | Current retry count |
| `max_retries` | `int` | `3` | Max retries |
| `timeout` | `int` | `60` | Timeout seconds |
| `status` | `TaskStatus` | `PENDING` | Current status |
| `result` | `Any` | `None` | Execution result |
| `error` | `str \| None` | `None` | Error message |
| `duration_ms` | `float` | `0.0` | Duration |
| `permission_request_id` | `str \| None` | `None` | Permission ref |
| `is_optional` | `bool` | `False` | Optional flag |

**`ExecutionResult`**
| Field | Type | Description |
|-------|------|-------------|
| `success` | `bool` | Overall success |
| `output` | `str` | Summary output |
| `warnings` | `list[str]` | Warning messages |
| `errors` | `list[str]` | Error messages |
| `duration_ms` | `float` | Total duration |
| `tool_results` | `list[dict]` | Per-tool results |
| `task_count` | `int` | Total tasks |
| `completed_count` | `int` | Successful |
| `failed_count` | `int` | Failed |
| `skipped_count` | `int` | Skipped |
| `retry_count` | `int` | Total retries |

### 2.6 Frontend Execution Types

**File:** `src/frontend/src/components/execution/types.ts`

```typescript
type ExecutionNodeStatus =
  | "pending" | "queued" | "planning" | "running" | "streaming"
  | "waiting" | "waiting_for_permission" | "retrying" | "paused"
  | "cancelled" | "completed" | "failed" | "skipped" | "partial_success"

interface ExecutionNode {
  id: string; capability: string; label: string;
  status: ExecutionNodeStatus; progress?: ExecutionProgress;
  startedAt?: string; completedAt?: string; durationMs?: number;
  error?: string; isOptional?: boolean;
}

interface ExecutionState {
  id: string; objective: string; status: ExecutionNodeStatus;
  nodes: ExecutionNode[]; progress: ExecutionProgress;
  logs: ExecutionLogEntry[]; result?: ExecutionResultData;
  permission?: PermissionRequest; error?: string;
  createdAt: string; startedAt?: string; completedAt?: string;
  durationMs?: number; owner?: string; priority?: number;
  conversationId?: string;
}

interface ExecutionSession {
  id: string; conversationId: string; requestId: string;
  title: string; status: ExecutionSessionStatus;
  startedAt: string; completedAt?: string; durationMs?: number;
  steps: ExecutionStep[]; logs: SessionLogEntry[];
  metadata: SessionMetadata; result?: SessionResult;
  error?: string; collapsed?: boolean;
}
```

**Execution Session Events:**
```typescript
type ExecutionSessionEvent =
  | { type: "ExecutionStarted"; sessionId: string; ... }
  | { type: "PlanningStarted"; sessionId: string }
  | { type: "PlanningCompleted"; sessionId: string; steps: number }
  | { type: "StepScheduled|StepStarted|StepUpdated|StepCompleted"; ... }
  | { type: "PermissionRequested|PermissionGranted"; ... }
  | { type: "ExecutionCompleted|ExecutionFailed|ExecutionCancelled"; ... }
```

### 2.7 REST API Routes (Backend)

**File:** `src/backend/aios/api/execution.py`

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/api/v1/execution/start` | Start execution |
| `GET` | `/api/v1/execution/{id}` | Get execution |
| `POST` | `/api/v1/execution/{id}/pause` | Pause |
| `POST` | `/api/v1/execution/{id}/resume` | Resume |
| `POST` | `/api/v1/execution/{id}/cancel` | Cancel |
| `GET` | `/api/v1/execution/{id}/progress` | Get progress |
| `GET` | `/api/v1/execution/{id}/events` | Stream events |
| `GET` | `/api/v1/execution/history` | List history |

**Events Published:** `execution.created`, `execution.started`, `execution.paused`, `execution.resumed`, `execution.completed`, `execution.failed`, `execution.cancelled`, `execution.planning_started`, `execution.planning_completed`, `execution.permission_requested`, `execution.permission_granted`, `execution.permission_denied`, `execution.task_*`, `execution.tool_*`, `execution.progress`, `execution.warning`, `execution.error`

**Extension Rules:** New execution statuses extend `ExecutionStatus` enum. New task types extend `Task` model.
**Future Compatibility:** Executor, Scheduler, and RecoveryEngine can have alternative implementations.

---

## 3. Memory APIs

### 3.1 Core Types (Frontend — TypeScript)

**File:** `src/frontend/src/memory/core/types.ts`

```typescript
type NodeSuperType = "action" | "observation" | "knowledge" | "artifact" | "entity" | "meta"
type NodeStatus = "active" | "archived" | "deleted"
type SortField = "createdAt" | "updatedAt" | "lastAccessed" | "importance" | "confidence" | "accessCount" | "title"

interface NodeId { readonly value: string; readonly type: string }
interface EdgeId { readonly value: string }

interface MemoryNode<TMetadata = Record<string, unknown>> {
  readonly id: NodeId; readonly type: string; readonly subtype: string;
  readonly title: string; readonly summary: string;
  readonly createdAt: number; readonly updatedAt: number; readonly lastAccessed: number;
  readonly source: string; readonly metadata: TMetadata;
  readonly tags: readonly string[]; readonly importance: number; readonly confidence: number;
  readonly accessCount: number; readonly pinned: boolean; readonly archived: boolean;
  readonly verified: boolean; readonly verificationMethod: string; readonly status: NodeStatus;
}

interface MemoryEdge<TMetadata = Record<string, unknown>> {
  readonly id: EdgeId; readonly sourceNodeId: NodeId; readonly targetNodeId: NodeId;
  readonly type: string; readonly strength: number; readonly weight: number;
  readonly metadata: TMetadata; readonly createdAt: number;
}

interface NodeInput {
  id?: string; type: string; subtype: string; title: string; summary?: string;
  source: string; metadata?: TMetadata; tags?: readonly string[];
  importance?: number; confidence?: number; pinned?: boolean; archived?: boolean;
  verified?: boolean; verificationMethod?: string; createdAt?: number; status?: NodeStatus;
}

interface EdgeInput {
  id?: string; sourceNodeId: NodeId; targetNodeId: NodeId; type: string;
  strength?: number; weight?: number; metadata?: TMetadata;
}

interface SearchFilters {
  types?: readonly string[]; superTypes?: readonly NodeSuperType[];
  projectIds?: readonly string[]; tags?: readonly string[];
  statuses?: readonly NodeStatus[]; sources?: readonly string[];
  dateFrom?: number; dateTo?: number;
  importanceMin?: number; importanceMax?: number;
  confidenceMin?: number; confidenceMax?: number;
  pinned?: boolean; archived?: boolean;
}

interface SearchQuery {
  keyword?: string; filters?: SearchFilters;
  relationship?: { seedNodeId: NodeId; filter: RelationshipFilter };
  options: QueryOptions;
}

interface SearchResult {
  nodes: readonly MemoryNode[]; total: number; hasMore: boolean; query: SearchQuery;
}

interface TraversalResult {
  nodes: readonly MemoryNode[]; edges: readonly MemoryEdge[]; depth: number; path?: readonly NodeId[];
}

interface MemorySnapshot {
  nodes: readonly MemoryNode[]; edges: readonly MemoryEdge[]; timestamp: number;
}

interface ValidationError {
  code: string; message: string; nodeId?: NodeId; edgeId?: EdgeId; field?: string;
}

interface MemoryGraphStats {
  totalNodes: number; totalEdges: number;
  bySuperType: Record<NodeSuperType, number>; byType: Record<string, number>;
  totalArchived: number; totalPinned: number; averageEdgesPerNode: number;
}
```

**Node Type Constants:**
```typescript
NodeTypeConstants = {
  CONVERSATION: "conversation", EXECUTION: "execution", WORKFLOW: "workflow",
  BROWSER_SESSION: "browser:session", BROWSER_PAGE: "browser:page", BROWSER_BOOKMARK: "browser:bookmark",
  VOICE_SESSION: "voice:session", VOICE_COMMAND: "voice:command",
  VISION_CAPTURE: "vision:capture", VISION_ANNOTATION: "vision:annotation",
  GENERATED_FILE: "file:generated", REFERENCED_FILE: "file:referenced",
  KNOWLEDGE_STATEMENT: "knowledge:statement", KNOWLEDGE_SUMMARY: "knowledge:summary",
  KNOWLEDGE_ENTITY: "knowledge:entity", ARTIFACT: "artifact",
  NOTE: "note", TEMPLATE: "template", PROJECT: "project",
  COLLECTION: "collection", TAG: "tag", PREFERENCE: "preference",
  REMINDER: "reminder", TASK: "task", PERSON: "person",
  ORGANIZATION: "organization", LOCATION: "location",
  PLUGIN_ACTION: "plugin:action", CUSTOM: "custom",
} as const
```

**Edge Type Constants:**
```typescript
EdgeTypeConstants = {
  CONTAINS: "contains", PRODUCES: "produces", DERIVES_FROM: "derives_from",
  REFERENCES: "references", BELONGS_TO: "belongs_to", GENERATED: "generated",
  USES: "uses", MENTIONS: "mentions", RELATED_TO: "related_to",
  PINNED: "pinned", SEQUENCES: "sequences", CONTRIBUTES_TO: "contributes_to",
  CONFIGURES: "configures", OBSERVES: "observes", TRANSFORMS: "transforms",
  CUSTOM: "custom",
} as const
```

### 3.2 `MemoryStore` (Frontend — TypeScript)

**Purpose:** Facade over the entire memory subsystem — graph, events, query, traversal, relationships.
**Owner:** Frontend Memory Core
**File:** `src/frontend/src/memory/core/store/MemoryStore.ts`
**Thread Safety:** Single-threaded (UI thread), subscription-based state sync

**Public Properties:**
| Property | Type | Description |
|----------|------|-------------|
| `graph` | `MemoryGraph` | Graph data structure |
| `events` | `MemoryEventBus` | Event pub/sub |
| `selectors` | `MemorySelectors` | Read-only queries |
| `query` | `QueryEngine` | Search/query execution |
| `traversal` | `GraphTraversal` | BFS/DFS/path finding |
| `relationships` | `RelationshipEngine` | Edge validation, cycles |
| `registry` | `MemoryRegistry` | Type & provider registry |

**Public Methods:**
| Method | Parameters | Returns | Error Conditions |
|--------|-----------|---------|-----------------|
| `addNode` | `input: NodeInput` | `MemoryNode` | — |
| `updateNode` | `id: NodeId, partial: Partial<MemoryNode>` | `MemoryNode \| undefined` | Not found |
| `deleteNode` | `id: NodeId` | `boolean` | Not found |
| `getNode` | `id: NodeId` | `MemoryNode \| undefined` | — |
| `addEdge` | `input: EdgeInput` | `MemoryEdge \| undefined` | Validation failure |
| `deleteEdge` | `id: EdgeId` | `boolean` | Not found |
| `search` | `query: SearchQuery` | `SearchResult` | — |
| `snapshot` | — | `MemorySnapshot` | — |
| `loadSnapshot` | `snapshot: MemorySnapshot` | `void` | — |
| `clear` | — | `void` | — |
| `onNodeEvent` | `eventType, handler: EventHandler` | `Unsubscribe` | — |
| `onEdgeEvent` | `eventType, handler: EventHandler` | `Unsubscribe` | — |
| `onAnyEvent` | `handler: EventHandler` | `Unsubscribe` | — |
| `subscribe` | `listener: () => void` | `Unsubscribe` | — |
| `getState` | — | `MemoryStoreState` | — |
| `getStats` | — | `MemoryGraphStats` | — |

**Singleton Accessors:**
```typescript
function getMemoryStore(): MemoryStore    // Returns default singleton
function setMemoryStore(store: MemoryStore): void  // Replace singleton
function resetMemoryStore(): void         // Clear singleton
```

### 3.3 `MemoryGraph` (Frontend — TypeScript)

**Purpose:** In-memory graph data structure with adjacency lists and type indexes.
**Owner:** Frontend Memory Core
**File:** `src/frontend/src/memory/core/graph/MemoryGraph.ts`

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `addNode` | `input: NodeInput` | `MemoryNode` | Create node |
| `updateNode` | `id: NodeId, partial` | `MemoryNode \| undefined` | Partial update |
| `deleteNode` | `id: NodeId` | `boolean` | Delete + cleanup edges |
| `getNode` | `id: NodeId` | `MemoryNode \| undefined` | Get + touch (updates access count) |
| `getNodeById` | `id: NodeId` | `MemoryNode \| undefined` | Get without touch |
| `hasNode` | `id: NodeId` | `boolean` | Existence check |
| `getAllNodes` | — | `readonly MemoryNode[]` | All nodes |
| `getNodesByType` | `type: string` | `readonly MemoryNode[]` | Filter by type |
| `getNodesBySuperType` | `superType: NodeSuperType` | `readonly MemoryNode[]` | Filter by supertype |
| `archiveNode` | `id: NodeId` | `MemoryNode \| undefined` | Set archived |
| `restoreNode` | `id: NodeId` | `MemoryNode \| undefined` | Unarchive |
| `addEdge` | `input: EdgeInput` | `MemoryEdge \| undefined` | Create edge |
| `deleteEdge` | `id: EdgeId` | `boolean` | Delete edge |
| `getEdge` | `id: EdgeId` | `MemoryEdge \| undefined` | Get edge |
| `getEdgesByNode` | `id: NodeId` | `readonly MemoryEdge[]` | All edges for node |
| `getOutgoingEdges` | `id: NodeId` | `readonly MemoryEdge[]` | Outgoing edges |
| `getIncomingEdges` | `id: NodeId` | `readonly MemoryEdge[]` | Incoming edges |
| `getOutgoingNeighbors` | `id: NodeId` | `readonly MemoryNode[]` | Outgoing neighbors |
| `getIncomingNeighbors` | `id: NodeId` | `readonly MemoryNode[]` | Incoming neighbors |
| `getNeighbors` | `id: NodeId` | `readonly MemoryNode[]` | All neighbors |
| `getConnectedEdges` | `id: NodeId` | `{ outgoing, incoming }` | Split edge view |
| `nodeCount` | — | `number` | Node count |
| `edgeCount` | — | `number` | Edge count |
| `snapshot` | — | `MemorySnapshot` | Full graph snapshot |
| `loadSnapshot` | `snapshot: MemorySnapshot` | `void` | Restore from snapshot |
| `clear` | — | `void` | Clear all data |
| `stats` | — | `MemoryGraphStats` | Statistics |

### 3.4 `GraphTraversal` (Frontend — TypeScript)

**Purpose:** Graph traversal algorithms (BFS, DFS, path finding).
**File:** `src/frontend/src/memory/core/graph/GraphTraversal.ts`

| Method | Parameters | Returns |
|--------|-----------|---------|
| `bfs` | `startId: NodeId, options?: { maxDepth?, edgeTypes? }` | `TraversalResult` |
| `dfs` | `startId: NodeId, options?: { maxDepth?, edgeTypes? }` | `TraversalResult` |
| `findPaths` | `startId: NodeId, endId: NodeId, options?` | `TraversalResult[]` |
| `findShortestPath` | `startId: NodeId, endId: NodeId, options?` | `TraversalResult \| undefined` |
| `getConnectedComponent` | `startId: NodeId` | `TraversalResult` |
| `getNeighborsAtDepth` | `id: NodeId, depth: number, options?` | `readonly MemoryNode[]` |

### 3.5 `RelationshipEngine` (Frontend — TypeScript)

**Purpose:** Edge validation, cycle detection, relationship summaries.
**File:** `src/frontend/src/memory/core/graph/RelationshipEngine.ts`

| Method | Parameters | Returns |
|--------|-----------|---------|
| `canAddEdge` | `input: EdgeInput` | `{ valid: boolean; errors: readonly ValidationError[] }` |
| `addEdge` | `input: EdgeInput` | `MemoryEdge \| undefined` |
| `deleteNodeWithEdges` | `id: NodeId` | `boolean` |
| `getConnectedComponent` | `id: NodeId` | `{ nodes, edges }` |
| `validateGraph` | — | `readonly ValidationError[]` |
| `findCycles` | — | `readonly CircularDependency[]` |
| `wouldCreateCycle` | `sourceId: NodeId, targetId: NodeId` | `CircularDependency \| undefined` |
| `getRelationshipSummary` | `id: NodeId` | `{ node, outgoingCount, incomingCount, totalConnections, connectedTypes }` |

### 3.6 `QueryEngine` (Frontend — TypeScript)

**Purpose:** Execute search queries with filters, sorting, pagination, and relationship traversal.
**File:** `src/frontend/src/memory/core/query/QueryEngine.ts`

| Method | Parameters | Returns |
|--------|-----------|---------|
| `execute` | `query: SearchQuery` | `SearchResult` |
| `findAll` | `options?: QueryOptions` | `SearchResult` |
| `findByType` | `type: string, options?: QueryOptions` | `SearchResult` |
| `findBySuperType` | `superType: string, options?` | `SearchResult` |
| `findByTag` | `tag: string, options?: QueryOptions` | `SearchResult` |
| `findBySource` | `source: string, options?: QueryOptions` | `SearchResult` |
| `searchByKeyword` | `keyword: string, options?: QueryOptions` | `SearchResult` |

### 3.7 `MemorySelectors` (Frontend — TypeScript)

**Purpose:** Read-only query helpers for common access patterns.
**File:** `src/frontend/src/memory/core/store/MemorySelectors.ts`

| Method | Parameters | Returns |
|--------|-----------|---------|
| `getRecentNodes` | `count = 10` | `readonly MemoryNode[]` |
| `getMostAccessedNodes` | `count = 10` | `readonly MemoryNode[]` |
| `getMostImportantNodes` | `count = 10` | `readonly MemoryNode[]` |
| `getHighestConfidenceNodes` | `count = 10` | `readonly MemoryNode[]` |
| `getPinnedNodes` | — | `readonly MemoryNode[]` |
| `getArchivedNodes` | — | `readonly MemoryNode[]` |
| `getActiveNodes` | — | `readonly MemoryNode[]` |
| `getNodesBySuperType` | `superType: NodeSuperType` | `readonly MemoryNode[]` |
| `getActionNodes` / `getObservationNodes` / `getKnowledgeNodes` / `getArtifactNodes` / `getEntityNodes` / `getMetaNodes` | — | `readonly MemoryNode[]` |
| `getNodesWithTag` | `tag: string` | `readonly MemoryNode[]` |
| `getNodesWithTags` | `tags: readonly string[], mode: "all" \| "any"` | `readonly MemoryNode[]` |
| `getNodesFromSource` | `source: string` | `readonly MemoryNode[]` |
| `getNodesByStatus` | `status: NodeStatus` | `readonly MemoryNode[]` |
| `getNodeCount` / `getEdgeCount` | — | `number` |
| `getEdgesForNode` | `id: NodeId` | `readonly MemoryEdge[]` |
| `getConnectedNodes` | `id: NodeId` | `readonly MemoryNode[]` |
| `getOutgoingConnections` / `getIncomingConnections` | `id: NodeId` | `readonly MemoryNode[]` |
| `search` | `keyword: string` | `readonly MemoryNode[]` |
| `findDuplicates` | `predicate: (a, b) => boolean` | `readonly [MemoryNode, MemoryNode][]` |
| `getStats` | — | `{ total, active, archived, pinned, bySuperType }` |

### 3.8 `MemoryEventBus` (Frontend — TypeScript)

**Purpose:** Type-safe event pub/sub for memory changes with history replay.
**File:** `src/frontend/src/memory/core/store/MemoryEvents.ts`

**Events:**
| Event Type | Payload |
|-----------|---------|
| `node:created` | `NodeChange` |
| `node:updated` | `NodeChange` (includes `previous`) |
| `node:deleted` | `NodeChange` |
| `node:archived` | `NodeChange` |
| `node:restored` | `NodeChange` |
| `edge:created` | `EdgeChange` |
| `edge:deleted` | `EdgeChange` |
| `relationship:changed` | `{ nodeId: NodeId; timestamp: number }` |
| `graph:cleared` | `{ timestamp: number }` |

**MemoryEventTypes constants:** `NodeCreated`, `NodeUpdated`, `NodeDeleted`, `NodeArchived`, `NodeRestored`, `EdgeCreated`, `EdgeDeleted`, `RelationshipChanged`, `GraphCleared`

**Public Methods:**
| Method | Parameters | Returns |
|--------|-----------|---------|
| `emit` | `event: MemoryEvent` | `void` |
| `on` | `eventType: string, handler: EventHandler` | `Unsubscribe` |
| `onAny` | `handler: EventHandler` | `Unsubscribe` |
| `once` | `eventType: string, handler: EventHandler` | `Unsubscribe` |
| `subscribe` | `subscriber: Subscriber` | `Unsubscribe` |
| `off` | `eventType: string, handler: EventHandler` | `void` |
| `getHistory` | `eventType?: string` | `readonly MemoryEvent[]` |
| `clearHistory` | — | `void` |
| `removeAllListeners` | `eventType?: string` | `void` |
| `listenerCount` | `eventType?: string` | `number` |

**Events Published:** See MemoryEvent discriminated union above.
**Extension Rules:** New node types add to `NodeTypeConstants`. New edge types add to `EdgeTypeConstants`. New super types extend `NodeSuperType` union.
**Future Compatibility:** MemoryStore can be backed by IndexedDB/SQLite via snapshot load/save. Provider system allows custom node/edge handlers.

---

## 4. Registry APIs

### 4.1 `MemoryRegistry` (Frontend — TypeScript)

**Purpose:** Central registry for node types, edge types, and memory providers.
**Owner:** Frontend Memory Core
**File:** `src/frontend/src/memory/core/registry/MemoryRegistry.ts`

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `registerNodeType` | `def: NodeTypeDefinition` | `this` | Register a node type |
| `registerEdgeType` | `def: EdgeTypeDefinition` | `this` | Register an edge type |
| `registerProvider` | `provider: MemoryProvider` | `this` | Register a provider |
| `getProvider` | `name: string` | `MemoryProvider \| undefined` | Get provider |
| `getProviders` | — | `readonly MemoryProvider[]` | All providers |
| `initialize` | — | `void` | Initialize all providers |
| `isInitialized` | — | `boolean` | Check initialized |
| `validateAll` | — | `readonly string[]` | Validate all types |
| `validateNodeType` | `type: string` | `boolean` | Validate type |
| `canConnect` | `sourceNodeId, edgeType, targetNodeId` | `boolean` | Validate edge |
| `getProvidersForNode` | `type: string` | `readonly MemoryProvider[]` | Matching providers |
| `count` | — | `{ nodeTypes, edgeTypes, providers }` | Counts |
| `reset` | — | `void` | Clear all |

**Singleton Accessors:** `getMemoryRegistry()`, `setMemoryRegistry()`, `resetMemoryRegistry()`

### 4.2 `NodeTypeRegistry` (Frontend — TypeScript)

**File:** `src/frontend/src/memory/core/registry/NodeTypeRegistry.ts`

| Method | Parameters | Returns |
|--------|-----------|---------|
| `register` | `def: NodeTypeDefinition` | `this` |
| `registerMany` | `defs: readonly NodeTypeDefinition[]` | `this` |
| `get` | `name: string` | `NodeTypeDefinition \| undefined` |
| `has` | `name: string` | `boolean` |
| `getAll` | — | `readonly NodeTypeDefinition[]` |
| `getBySuperType` | `superType: NodeSuperType` | `readonly NodeTypeDefinition[]` |
| `getAllowedEdgeTypes` | `nodeType: string` | `readonly string[]` |
| `isValidNodeType` | `nodeType: string` | `boolean` |
| `isAllowedEdgeType` | `nodeType: string, edgeType: string` | `boolean` |
| `validateNodeId` | `nodeId: NodeId` | `boolean` |
| `getDefaultMetadata` | `nodeType: string` | `Record<string, unknown>` |
| `count` / `clear` | — | `number` / `void` |

### 4.3 `EdgeTypeRegistry` (Frontend — TypeScript)

**File:** `src/frontend/src/memory/core/registry/EdgeTypeRegistry.ts`

| Method | Parameters | Returns |
|--------|-----------|---------|
| `register` | `def: EdgeTypeDefinition` | `this` |
| `registerMany` | `defs: readonly EdgeTypeDefinition[]` | `this` |
| `get` | `name: string` | `EdgeTypeDefinition \| undefined` |
| `has` | `name: string` | `boolean` |
| `getAll` | — | `readonly EdgeTypeDefinition[]` |
| `canConnect` | `sourceType, edgeType, targetType` | `boolean` |
| `getAllowedSourceTypes` | `edgeType: string` | `readonly string[]` |
| `getAllowedTargetTypes` | `edgeType: string` | `readonly string[]` |
| `isDirectional` | `edgeType: string` | `boolean` |
| `getDefaultMetadata` | `edgeType: string` | `Record<string, unknown>` |
| `count` / `clear` | — | `number` / `void` |

### 4.4 `NodeTypeDefinition` / `EdgeTypeDefinition` (Frontend — TypeScript)

```typescript
interface NodeTypeDefinition {
  readonly name: string
  readonly superType: NodeSuperType
  readonly description: string
  readonly allowedEdgeTypes: readonly string[]
  readonly allowedAsTargetFor: readonly string[]
  readonly defaultMetadata: Record<string, unknown>
}

interface EdgeTypeDefinition {
  readonly name: string
  readonly description: string
  readonly allowedSourceTypes: readonly string[]
  readonly allowedTargetTypes: readonly string[]
  readonly directional: boolean
  readonly defaultMetadata: Record<string, unknown>
}
```

### 4.5 `MemoryProvider` Interface (Frontend — TypeScript)

```typescript
interface MemoryProvider {
  readonly name: string
  readonly registerTypes: () => void
  readonly canHandleNode: (node: MemoryNode) => boolean
  readonly canHandleEdge: (edge: MemoryEdge) => boolean
  readonly validate: () => readonly string[]
}
```

### 4.6 `CommandRegistry` (Frontend — TypeScript)

**Purpose:** Register and search commands across static and provider-based sources.
**Owner:** Frontend Command Center
**File:** `src/frontend/src/components/command/CommandRegistry.ts`

| Method | Parameters | Returns |
|--------|-----------|---------|
| `subscribe` | `listener: () => void` | `() => void` |
| `registerProvider` | `provider: CommandProvider` | `void` |
| `unregisterProvider` | `id: string` | `void` |
| `getProvider` | `id: string` | `CommandProvider \| undefined` |
| `getAllProviders` | — | `CommandProvider[]` |
| `setStaticCommands` | `commands: CommandItem[]` | `void` |
| `addStaticCommand` | `command: CommandItem` | `void` |
| `getStaticCommands` | — | `CommandItem[]` |
| `searchAll` | `query: string` | `Promise<CommandItem[]>` |
| `getAllCommands` | — | `CommandItem[]` |

**Singleton Accessor:** `getCommandRegistry(): CommandRegistry`

### 4.7 REST API Routes — Capabilities

**File:** `src/backend/aios/api/capabilities.py`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/capabilities` | List capabilities (optional `?tag=`) |
| `POST` | `/capabilities/search` | Search capabilities |
| `POST` | `/capabilities/rank` | Rank by task relevance |
| `GET` | `/capabilities/{id}/recommend` | Recommend alternatives |
| `GET` | `/capabilities/filter/by-interface/{interface}` | Filter by interface |
| `GET` | `/capabilities/filter/by-permission` | Filter by permission level |

**Extension Rules:** New registries follow the same pattern: `register()`, `get()`, `getAll()`, `validateXxx()`, singleton accessor.
**Future Compatibility:** Registry pattern allows any feature to register its types without modifying core.

---

## 5. Command APIs

### 5.1 Command Types (Frontend — TypeScript)

**File:** `src/frontend/src/components/command/types.ts`

```typescript
type CommandCategory =
  | "app" | "workspace" | "tool" | "plugin" | "conversation"
  | "session" | "memory" | "browser" | "voice" | "vision"
  | "developer" | "file" | "nlp" | "recent"

type CommandResultType =
  | "open-workspace" | "open-conversation" | "open-session"
  | "execute-tool" | "open-panel" | "nlp-query" | "open-url"
  | "run-command" | "run-plugin" | "search-query"

interface CommandItem {
  id: string; name: string; description: string;
  category: CommandCategory; resultType: CommandResultType;
  icon?: string; shortcut?: string; keywords?: string[];
  payload?: unknown; action: () => void; highlight?: boolean;
}

interface CommandProvider {
  id: string; name: string; commands: CommandItem[];
  search(query: string): Promise<CommandItem[]>;
  refresh?(): Promise<void>;
}

interface CommandHistoryEntry {
  commandId: string; executedAt: string; pinned?: boolean;
}

interface NaturalLanguageIntent {
  text: string; intent: string; confidence: number;
  suggestedCommand?: CommandItem; resultType: CommandResultType; payload?: unknown;
}
```

### 5.2 `CommandStore` (Frontend — TypeScript)

**Purpose:** State management for the command palette with history, pinning, and search.
**Owner:** Frontend Command Center
**File:** `src/frontend/src/components/command/CommandStore.ts`

| Method | Parameters | Returns |
|--------|-----------|---------|
| `getState` | — | `CommandStoreState` |
| `subscribe` | `listener: () => void` | `() => void` |
| `setState` | `partial: Partial<CommandStoreState>` | `void` |
| `setQuery` | `query: string` | `void` (debounced search) |
| `selectNext` / `selectPrevious` | — | `void` |
| `getSelectedItem` | — | `CommandItem \| null` |
| `recordExecution` | `commandId: string` | `void` |
| `togglePin` | `commandId: string` | `void` |
| `isPinned` | `commandId: string` | `boolean` |
| `clearHistory` | — | `void` |
| `reset` | — | `void` |
| `getRecentCommands` | `allCommands: Map<string, CommandItem>` | `CommandItem[]` |

**`CommandStoreState`:**
```typescript
interface CommandStoreState {
  query: string; results: CommandItem[]; groups: CommandGroup[];
  selectedIndex: number; loading: boolean; error: string | null;
  recentCommands: CommandHistoryEntry[]; pinnedCommands: string[];
}
```

**Singleton Accessor:** `getCommandStore(): CommandStore`

**Events Consumed:** Commands are registered via `CommandRegistry.registerProvider()`.
**Extension Rules:** New categories add to `CommandCategory` union. New result types add to `CommandResultType`.
**Future Compatibility:** Providers can be lazily registered, search is async.

---

## 6. Workspace APIs

### 6.1 Backend Interfaces

**File:** `src/backend/aios/workspace/interfaces.py`

**`IWorkspaceSensor`**
| Method | Parameters | Returns |
|--------|-----------|---------|
| `collect` | — | `dict` |
| `start` | — | `None` |
| `stop` | — | `None` |

**`IProjectDetector`**
| Method | Parameters | Returns |
|--------|-----------|---------|
| `detect` | `path: str` | `Project \| None` |

**`IWorkspaceManager`**
| Method | Parameters | Returns |
|--------|-----------|---------|
| `get_current_snapshot` | — | `WorkspaceSnapshot` |
| `refresh` | — | `WorkspaceSnapshot` |

**`IWorkspaceCache`**
| Method | Parameters | Returns |
|--------|-----------|---------|
| `get_snapshot` | — | `WorkspaceSnapshot \| None` |
| `update_snapshot` | `snapshot: WorkspaceSnapshot` | `None` |

### 6.2 Workspace Models (Backend — Python)

**File:** `src/backend/aios/workspace/models.py`

**`WorkspaceSnapshot`**
| Field | Type | Description |
|-------|------|-------------|
| `timestamp` | `datetime` | Snapshot time |
| `active_window` | `str` | Active window title |
| `active_application` | `Application \| None` | Foreground app |
| `applications` | `list` | Running applications |
| `projects` | `list` | Detected projects |
| `repositories` | `list` | Git repositories |
| `editors` | `list` | Open editors |
| `terminals` | `list` | Open terminals |

**`Application`** — `process_name`, `window_title`, `executable`, `pid`, `category: AppCategory`
**`Project`** — `root_path`, `name`, `framework: FrameworkType`, `language`, `package_manager`, `build/test/run_command`
**`Repository`** — `provider`, `branch`, `remote`, `modified/staged/untracked_files`, `status: GitStatus`
**`Editor`** — `name`, `workspace`, `active_file`, `file_language`, `pid`
**`Terminal`** — `cwd`, `shell`, `pid`

**FrameworkType enum values:** `NEXT_JS`, `REACT`, `VUE`, `ANGULAR`, `NODE_JS`, `FASTAPI`, `DJANGO`, `FLASK`, `PYTHON`, `FLUTTER`, `REACT_NATIVE`, `DOTNET`, `JAVA`, `RUST`, `GO`, `UNKNOWN`

### 6.3 Frontend Workspace Registry

**File:** `src/frontend/src/components/workspace/WorkspaceRegistry.tsx`

```typescript
interface WorkspaceDefinition {
  id: string; label: string; icon?: string; component: ComponentType<any>;
}

interface WorkspaceRegistryProps {
  workspaces: WorkspaceDefinition[]; activeId: string;
  fallback?: ComponentType<{ workspaceId: string }>;
}
```

### 6.4 REST API Routes

**File:** `src/backend/aios/api/workspace.py`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/workspace/current` | Current snapshot |
| `GET` | `/workspace/projects` | Detected projects |
| `GET` | `/workspace/applications` | Running apps |
| `GET` | `/workspace/git` | Git status |
| `GET` | `/workspace/editors` | Open editors |
| `GET` | `/workspace/terminals` | Open terminals |
| `GET` | `/workspace/history` | Snapshot history |
| `POST` | `/workspace/refresh` | Force refresh |

### 6.5 Frontend API Client

**File:** `src/frontend/src/services/api.ts`

```typescript
api.desktop.status(): Promise<Response>
api.desktop.statusHistory(limit: number): Promise<Response>
api.desktop.settings.get/update(settings): Promise<Response>
api.desktop.hotkeys.get/update(action, combination): Promise<Response>
api.desktop.notifications.history/clear(): Promise<Response>
api.desktop.window.state/show/hide/minimize/restore(): Promise<Response>
api.desktop.startup.status/enable/disable(): Promise<Response>
```

**Extension Rules:** New project detectors extend `IProjectDetector`. New workspace types add to `WorkspaceDefinition[]`.
**Future Compatibility:** Sensor system allows platform-specific implementations.

---

## 7. Plugin APIs

### 7.1 `AIOSPlugin` (Backend — Python)

**Purpose:** Base class for all plugins. Plugin authors inherit from this.
**Owner:** Backend Plugin System
**File:** `src/backend/aios/plugins/sdk.py`

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `initialize` | — | `None` | Load resources, required |
| `register` | — | `None` | Register tools/capabilities/events, required |
| `start` | — | `None` | Start background tasks |
| `health` | — | `Dict[str, Any]` | Return health status |
| `stop` | — | `None` | Stop background tasks |
| `shutdown` | — | `None` | Cleanup before unload |
| `dispose` | — | `None` | Final cleanup on removal |
| `publish_event` | `event_type: str, payload: Dict` | `None` | Publish to Event Bus |
| `request_permission` | `permission: str, level: int, reason: str` | `bool` | Request permission |
| `register_tool` | `tool_definition: Dict` | `bool` | Register tool |
| `register_capability` | `capability: PluginCapability` | `bool` | Register capability |
| `get_setting` | `key: str, default: Any` | `Any` | Get plugin setting |
| `log_info` / `log_error` / `log_warning` / `log_debug` | `message: str` | `None` | Logging |

**Properties:** `plugin_id` (str), `plugin_name` (str), `metadata` (PluginManifest)
**Lifecycle:** `initialize()` → `register()` → `start()` → `stop()` → `shutdown()` → `dispose()`

### 7.2 Plugin Models (Backend — Python)

**File:** `src/backend/aios/plugins/models.py`

**`Plugin`**
| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique ID |
| `manifest` | `PluginManifest \| None` | Plugin manifest |
| `state` | `PluginState` | Current state |
| `scope` | `PluginScope` | builtin/user/system/marketplace |
| `source` | `str` | Source path/URL |
| `instance` | `Any` | Plugin instance |
| `capabilities` | `list[PluginCapability]` | Registered capabilities |
| `dependencies` | `list[PluginDependency]` | Dependencies |

**`PluginStatus` enum:** `DISCOVERED`, `VALIDATED`, `VERIFIED`, `LOADING`, `LOADED`, `INITIALIZING`, `STARTING`, `ACTIVE`, `STOPPING`, `STOPPED`, `DISABLED`, `DEGRADED`, `FAILED`, `UNLOADED`, `REMOVED`

**`PluginCapability`:** `id`, `name`, `description`, `permission_level`, `timeout`, `parameters`, `returns`, `tags`
**`PluginPermission`:** `permission`, `level`, `reason`, `granted`
**`PluginHealth`:** `status`, `startup_time_ms`, `memory_usage_mb`, `error_count`, `restart_count`, `last_error`, `uptime_seconds`
**`PluginConfiguration`:** `plugin_id`, `settings`, `enabled`, `auto_start`, `isolation: IsolationStrategy`
**`PluginResult`:** `success`, `data`, `error`, `duration_ms`

### 7.3 REST API Routes — Plugins

**File:** `src/backend/aios/api/plugins.py`

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/plugins` | List plugins (optional `?search=`) |
| `GET` | `/plugins/{id}` | Get plugin |
| `POST` | `/plugins/install` | Install plugin |
| `POST` | `/plugins/{id}/enable` | Enable |
| `POST` | `/plugins/{id}/disable` | Disable |
| `POST` | `/plugins/{id}/reload` | Reload |
| `DELETE` | `/plugins/{id}` | Remove |
| `GET` | `/plugins/health` | Aggregate health |
| `GET` | `/plugins/{id}/health` | Plugin health |
| `GET` | `/plugins/{id}/manifest` | Get manifest |
| `GET` | `/plugins/{id}/capabilities` | List capabilities |
| `GET` | `/plugins/{id}/permissions` | List permissions |
| `GET` | `/plugins/{id}/config` | Get config |
| `PUT` | `/plugins/{id}/config` | Update config |

### 7.4 Frontend API Client

**File:** `src/frontend/src/services/api.ts`

```typescript
api.plugins.list(search?: string): Promise<Response>
api.plugins.get(id: string): Promise<Response>
api.plugins.install(path: string, enable: boolean): Promise<Response>
api.plugins.enable/disable/reload(id: string): Promise<Response>
api.plugins.remove(id: string): Promise<Response>
api.plugins.health(): Promise<Response>
api.plugins.getHealth/getManifest/getCapabilities/getPermissions(id: string): Promise<Response>
api.plugins.getConfig/updateConfig(id: string, config: Record<string, unknown>): Promise<Response>
```

**Extension Rules:** Plugin lifecycle can be extended by overriding `AIOSPlugin` methods. New isolation strategies add to `IsolationStrategy` enum.
**Future Compatibility:** Plugin SDK is stable — new platform features add to `_inject_services()`.

---

## 8. Capability APIs

### 8.1 `Capability` / `CapabilityRegistry` (Backend — Python)

**Purpose:** Registry for discovering, ranking, and filtering capabilities by intent.
**Owner:** Backend Core
**File:** `src/backend/aios/core/capability_registry.py`

**`Capability` dataclass:**
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `id` | `str` | — | Unique capability ID |
| `name` | `str` | — | Display name |
| `description` | `str` | — | Description |
| `provider_type` | `str` | — | Provider category |
| `provider_id` | `str` | — | Provider identifier |
| `parameters` | `dict` | `{}` | Input schema |
| `returns` | `dict` | `{}` | Output schema |
| `permission_level` | `int` | `0` | Required level |
| `tags` | `list[str]` | `[]` | Search tags |
| `version` | `str` | `"1.0.0"` | Version |
| `quality` | `float` | `1.0` | Quality score |
| `supported_interfaces` | `list[str]` | `["chat"]` | Interfaces |
| `supports_streaming` | `bool` | `False` | Streaming support |
| `supports_cancellation` | `bool` | `False` | Cancellation |
| `estimated_latency` | `float` | `0.0` | Expected latency |
| `estimated_cost` | `float` | `0.0` | Cost estimate |
| `reliability_score` | `float` | `1.0` | Reliability |
| `requires_confirmation` | `bool` | `False` | User confirmation |
| `related_capabilities` | `list[str]` | `[]` | Related IDs |

**`CapabilityRegistry` methods:**
| Method | Parameters | Returns |
|--------|-----------|---------|
| `register_capability` | `capability: Capability` | `None` |
| `unregister_capability` | `capability_id: str` | `None` |
| `register_provider` | `provider_type: str, provider: Any` | `None` |
| `find_capability` | `query: str, context?: dict` | `list[Capability]` |
| `find_best_match` | `query: str, context?: dict` | `Capability \| None` |
| `list_capabilities` | `tag?: str` | `list[Capability]` |
| `search_capabilities` | `query: str` | `list[Capability]` |
| `search_by_category` | `category: str` | `list[Capability]` |
| `filter_by_permission` | `min_level: int, max_level?: int` | `list[Capability]` |
| `filter_by_interface` | `interface: str` | `list[Capability]` |
| `rank_for_task` | `task_description: str, context?: dict` | `list[tuple[Capability, float]]` |
| `recommend_alternatives` | `capability_id: str, max_results: int` | `list[Capability]` |

### 8.2 Frontend API Client

```typescript
api.capabilities.list(tag?: string): Promise<Response>
api.capabilities.search(query: string, limit?: number): Promise<Response>
api.capabilities.get(id: string): Promise<Response>
api.capabilities.rank(query: string, limit?: number): Promise<Response>
api.capabilities.recommend(id: string, maxResults?: number): Promise<Response>
api.capabilities.filterByInterface(interfaceName: string): Promise<Response>
api.capabilities.filterByPermission(minLevel: number, maxLevel?: number): Promise<Response>
```

**Extension Rules:** New capabilities add `Capability` instances. New provider types add to `register_provider()`.
**Future Compatibility:** Ranking algorithm can be swapped without changing the interface.

---

## 9. Store APIs

### 9.1 `MemoryStore` (Frontend — TypeScript)

*(Full documentation in section 3.2)*

### 9.2 `CommandStore` (Frontend — TypeScript)

*(Full documentation in section 5.2)*

### 9.3 `ExecutionSessionStore` (Frontend — TypeScript)

**File:** `src/frontend/src/components/execution/session/ExecutionSessionStore.ts`

| Method | Parameters | Returns |
|--------|-----------|---------|
| `getSession` | `id: string` | `ExecutionSession \| undefined` |
| `getAllSessions` | — | `ExecutionSession[]` |
| `addSession` | `session: ExecutionSession` | `void` |
| `updateSession` | `id: string, partial` | `void` |
| `removeSession` | `id: string` | `void` |
| `clear` | — | `void` |

**Extension Rules:** New stores follow singleton pattern with `getXxxStore()`, `setXxxStore()`, `resetXxxStore()`.
**Future Compatibility:** Stores can be backed by persistence via snapshot/load.

---

## 10. Event APIs

### 10.1 `EventBus` (Backend — Python)

**Purpose:** Async event-driven communication backbone.
**Owner:** Backend Core
**File:** `src/backend/aios/core/event_bus.py`

| Method | Parameters | Returns | Description |
|--------|-----------|---------|-------------|
| `start` | — | `None` | Start dispatch loop |
| `stop` | — | `None` | Stop dispatch loop |
| `publish` | `event_type: str, payload: dict, source: str, correlation_id: str, priority: int` | `str` (event ID) | Publish event |
| `subscribe` | `event_type: str, handler: Callable` | `str` (sub ID) | Subscribe |
| `unsubscribe` | `subscription_id: str` | `bool` | Unsubscribe |
| `get_history` | `event_type?: str, limit: int = 100` | `list[Event]` | Event history |

**`Event` dataclass:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | `str` | Unique ID |
| `type` | `str` | Event type string |
| `source` | `str` | Source module |
| `timestamp` | `datetime` | Creation time |
| `payload` | `dict` | Event data |
| `correlation_id` | `str` | Trace ID |
| `retry_count` | `int` | Delivery attempts |
| `priority` | `int` | Priority (higher = first) |

### 10.2 `MemoryEventBus` (Frontend — TypeScript)

*(Full documentation in section 3.8)*

### 10.3 `ExecutionEventPublisher` (Backend — Python)

**Purpose:** Publishes execution lifecycle events.
**File:** `src/backend/aios/execution/events.py`

**Event types published:**
```
execution.created, execution.started, execution.paused, execution.resumed,
execution.completed, execution.failed, execution.cancelled,
execution.planning_started, execution.planning_completed,
execution.permission_requested, execution.permission_granted, execution.permission_denied,
execution.task_queued, execution.task_started, execution.task_completed, execution.task_failed, execution.task_retrying,
execution.tool_executing, execution.tool_completed,
execution.warning, execution.error, execution.progress
```

**Events Consumed (by EventBus):** Any `.publish()` call from any module.
**Extension Rules:** New event types use `.*` wildcard matching. Events are immutable — never mutate in handlers.
**Future Compatibility:** EventBus supports wildcard subscriptions (`*` and `prefix.*`). Max 10000 event history with auto-prune to 5000.

---

## 11. Provider APIs

### 11.1 `MemoryProvider` (Frontend — TypeScript)

```typescript
interface MemoryProvider {
  readonly name: string
  readonly registerTypes: () => void      // Register node/edge types
  readonly canHandleNode: (node: MemoryNode) => boolean
  readonly canHandleEdge: (edge: MemoryEdge) => boolean
  readonly validate: () => readonly string[]
}
```

### 11.2 `CommandProvider` (Frontend — TypeScript)

```typescript
interface CommandProvider {
  id: string
  name: string
  commands: CommandItem[]
  search(query: string): Promise<CommandItem[]>
  refresh?(): Promise<void>
}
```

### 11.3 `AIProvider` (Backend — Python)

**File:** `src/backend/aios/core/ai_router.py`

Abstract base class for AI model providers. Methods:
- `generate(request: AIRequest) -> AIResponse` — Generate text
- `stream(request: AIRequest) -> AsyncIterator[dict]` — Stream response

### 11.4 Backend Interface Providers

| Interface | File | Key Methods |
|-----------|------|-------------|
| `IWorkspaceSensor` | `src/backend/aios/workspace/interfaces.py` | `collect()`, `start()`, `stop()` |
| `IProjectDetector` | `src/backend/aios/workspace/interfaces.py` | `detect(path: str) -> Project \| None` |
| `IWorkspaceManager` | `src/backend/aios/workspace/interfaces.py` | `get_current_snapshot()`, `refresh()` |
| `IWorkspaceCache` | `src/backend/aios/workspace/interfaces.py` | `get_snapshot()`, `update_snapshot()` |
| `IExecutionEngine` | `src/backend/aios/execution/interfaces.py` | `start_execution()`, `pause/resume/cancel()` |
| `IExecutor` | `src/backend/aios/execution/interfaces.py` | `execute_task()`, `validate_task()` |
| `IScheduler` | `src/backend/aios/execution/interfaces.py` | `schedule()`, `cancel()`, `pause()`, `resume()` |
| `IRecoveryEngine` | `src/backend/aios/execution/interfaces.py` | `handle_failure()`, `can_continue()` |
| `IConversationRepository` | `src/backend/aios/conversation/interfaces.py` | Storage CRUD |
| `IConversationService` | `src/backend/aios/conversation/interfaces.py` | Business logic |

**Extension Rules:** New providers implement the relevant interface. Providers register via `register_provider()` on the relevant registry.
**Future Compatibility:** All provider interfaces are designed for alternative implementations (e.g., different AI providers, different storage backends).

---

# Architecture-Wide Contracts

## Error Handling
- Backend: Methods raise typed exceptions or return `None`/empty for not-found
- Frontend: Methods return `undefined` or `null` for not-found; errors propagated via event system
- Plugins: `PluginResult` with `success`, `data`, `error` pattern

## Thread Safety
- Backend: All interfaces are async-safe (Python `asyncio`)
- Frontend: Single-threaded (UI thread); stores use subscription-based state sync

## Versioning
- Backward-compatible method signatures maintained
- Breaking changes require ADR
- Capability versions tracked via `Capability.version`

## Extension Rules
- Registries: `registerXxx()` pattern
- Providers: Implement interface, register via registry
- Events: New types use reverse-domain style (`domain:action`)
- Types: Extend via union types (TS) or enum values (Python)

---

# Document Status

**Status:** Active
**Type:** Living API Specification
**Maintained by:** ADR process + code review
**Next Review:** After completion of each remaining implementation phase
