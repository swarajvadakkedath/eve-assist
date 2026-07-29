export type NodeSuperType = "action" | "observation" | "knowledge" | "artifact" | "entity" | "meta"

export type NodeStatus = "active" | "archived" | "deleted"

export type EdgeDirection = "outgoing" | "incoming" | "both"

export type SortOrder = "asc" | "desc"

export type SortField =
  | "createdAt"
  | "updatedAt"
  | "lastAccessed"
  | "importance"
  | "confidence"
  | "accessCount"
  | "title"

export interface NodeId {
  readonly value: string
  readonly type: string
}

export interface EdgeId {
  readonly value: string
}

export interface MemoryNode<TMetadata = Record<string, unknown>> {
  readonly id: NodeId
  readonly type: string
  readonly subtype: string
  readonly title: string
  readonly summary: string
  readonly createdAt: number
  readonly updatedAt: number
  readonly lastAccessed: number
  readonly source: string
  readonly metadata: TMetadata
  readonly tags: readonly string[]
  readonly importance: number
  readonly confidence: number
  readonly accessCount: number
  readonly pinned: boolean
  readonly archived: boolean
  readonly verified: boolean
  readonly verificationMethod: string
  readonly status: NodeStatus
}

export interface MemoryEdge<TMetadata = Record<string, unknown>> {
  readonly id: EdgeId
  readonly sourceNodeId: NodeId
  readonly targetNodeId: NodeId
  readonly type: string
  readonly strength: number
  readonly weight: number
  readonly metadata: TMetadata
  readonly createdAt: number
}

export interface NodeTypeDefinition {
  readonly name: string
  readonly superType: NodeSuperType
  readonly description: string
  readonly allowedEdgeTypes: readonly string[]
  readonly allowedAsTargetFor: readonly string[]
  readonly defaultMetadata: Record<string, unknown>
}

export interface EdgeTypeDefinition {
  readonly name: string
  readonly description: string
  readonly allowedSourceTypes: readonly string[]
  readonly allowedTargetTypes: readonly string[]
  readonly directional: boolean
  readonly defaultMetadata: Record<string, unknown>
}

export interface MemoryProvider {
  readonly name: string
  readonly registerTypes: () => void
  readonly canHandleNode: (node: MemoryNode) => boolean
  readonly canHandleEdge: (edge: MemoryEdge) => boolean
  readonly validate: () => readonly string[]
}

export interface NodeChange {
  readonly type: "created" | "updated" | "deleted" | "archived" | "restored"
  readonly node: MemoryNode
  readonly previous?: MemoryNode
  readonly timestamp: number
}

export interface EdgeChange {
  readonly type: "created" | "deleted"
  readonly edge: MemoryEdge
  readonly timestamp: number
}

export type MemoryEvent =
  | { readonly type: "node:created"; readonly payload: NodeChange }
  | { readonly type: "node:updated"; readonly payload: NodeChange }
  | { readonly type: "node:deleted"; readonly payload: NodeChange }
  | { readonly type: "node:archived"; readonly payload: NodeChange }
  | { readonly type: "node:restored"; readonly payload: NodeChange }
  | { readonly type: "edge:created"; readonly payload: EdgeChange }
  | { readonly type: "edge:deleted"; readonly payload: EdgeChange }
  | { readonly type: "relationship:changed"; readonly payload: { readonly nodeId: NodeId; readonly timestamp: number } }
  | { readonly type: "graph:cleared"; readonly payload: { readonly timestamp: number } }

export interface SearchFilters {
  readonly types?: readonly string[]
  readonly superTypes?: readonly NodeSuperType[]
  readonly projectIds?: readonly string[]
  readonly tags?: readonly string[]
  readonly statuses?: readonly NodeStatus[]
  readonly sources?: readonly string[]
  readonly dateFrom?: number
  readonly dateTo?: number
  readonly importanceMin?: number
  readonly importanceMax?: number
  readonly confidenceMin?: number
  readonly confidenceMax?: number
  readonly pinned?: boolean
  readonly archived?: boolean
}

export interface RelationshipFilter {
  readonly edgeTypes?: readonly string[]
  readonly maxDepth?: number
  readonly direction?: EdgeDirection
}

export interface QueryOptions {
  readonly sortField?: SortField
  readonly sortOrder?: SortOrder
  readonly limit?: number
  readonly offset?: number
}

export interface SearchQuery {
  readonly keyword?: string
  readonly filters?: SearchFilters
  readonly relationship?: {
    readonly seedNodeId: NodeId
    readonly filter: RelationshipFilter
  }
  readonly options: QueryOptions
}

export interface SearchResult {
  readonly nodes: readonly MemoryNode[]
  readonly total: number
  readonly hasMore: boolean
  readonly query: SearchQuery
}

export interface TraversalResult {
  readonly nodes: readonly MemoryNode[]
  readonly edges: readonly MemoryEdge[]
  readonly depth: number
  readonly path?: readonly NodeId[]
}

export interface ValidationError {
  readonly code: string
  readonly message: string
  readonly nodeId?: NodeId
  readonly edgeId?: EdgeId
  readonly field?: string
}

export interface CircularDependency {
  readonly path: readonly NodeId[]
  readonly edge: MemoryEdge
}

export interface MemorySnapshot {
  readonly nodes: readonly MemoryNode[]
  readonly edges: readonly MemoryEdge[]
  readonly timestamp: number
}

export interface Subscriber {
  readonly id: string
  readonly callback: (event: MemoryEvent) => void
  readonly filter?: (event: MemoryEvent) => boolean
}

export type Unsubscribe = () => void

export type EventHandler = (event: MemoryEvent) => void

export interface MemoryGraphStats {
  readonly totalNodes: number
  readonly totalEdges: number
  readonly bySuperType: Record<NodeSuperType, number>
  readonly byType: Record<string, number>
  readonly totalArchived: number
  readonly totalPinned: number
  readonly averageEdgesPerNode: number
}

export interface NodeInput<TMetadata = Record<string, unknown>> {
  readonly id?: string
  readonly type: string
  readonly subtype: string
  readonly title: string
  readonly summary?: string
  readonly source: string
  readonly metadata?: TMetadata
  readonly tags?: readonly string[]
  readonly importance?: number
  readonly confidence?: number
  readonly pinned?: boolean
  readonly archived?: boolean
  readonly verified?: boolean
  readonly verificationMethod?: string
  readonly createdAt?: number
  readonly status?: NodeStatus
}

export interface EdgeInput<TMetadata = Record<string, unknown>> {
  readonly id?: string
  readonly sourceNodeId: NodeId
  readonly targetNodeId: NodeId
  readonly type: string
  readonly strength?: number
  readonly weight?: number
  readonly metadata?: TMetadata
}

export const NodeTypeConstants = {
  CONVERSATION: "conversation",
  EXECUTION: "execution",
  WORKFLOW: "workflow",
  BROWSER_SESSION: "browser:session",
  BROWSER_PAGE: "browser:page",
  BROWSER_BOOKMARK: "browser:bookmark",
  VOICE_SESSION: "voice:session",
  VOICE_COMMAND: "voice:command",
  VISION_CAPTURE: "vision:capture",
  VISION_ANNOTATION: "vision:annotation",
  GENERATED_FILE: "file:generated",
  REFERENCED_FILE: "file:referenced",
  KNOWLEDGE_STATEMENT: "knowledge:statement",
  KNOWLEDGE_SUMMARY: "knowledge:summary",
  KNOWLEDGE_ENTITY: "knowledge:entity",
  ARTIFACT: "artifact",
  NOTE: "note",
  TEMPLATE: "template",
  PROJECT: "project",
  COLLECTION: "collection",
  TAG: "tag",
  PREFERENCE: "preference",
  REMINDER: "reminder",
  TASK: "task",
  PERSON: "person",
  ORGANIZATION: "organization",
  LOCATION: "location",
  PLUGIN_ACTION: "plugin:action",
  CUSTOM: "custom",
} as const

export const EdgeTypeConstants = {
  CONTAINS: "contains",
  PRODUCES: "produces",
  DERIVES_FROM: "derives_from",
  REFERENCES: "references",
  BELONGS_TO: "belongs_to",
  GENERATED: "generated",
  USES: "uses",
  MENTIONS: "mentions",
  RELATED_TO: "related_to",
  PINNED: "pinned",
  SEQUENCES: "sequences",
  CONTRIBUTES_TO: "contributes_to",
  CONFIGURES: "configures",
  OBSERVES: "observes",
  TRANSFORMS: "transforms",
  CUSTOM: "custom",
} as const
