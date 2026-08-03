import { useState, useMemo, useCallback } from "react";
import type { HTMLAttributes } from "react";
import type { MemoryNode as MemoryNodeType, SortField, SortOrder, NodeSuperType } from "@/memory/core";
import { getMemoryStore, NodeTypeConstants } from "@/memory/core";
import { MemoryToolbar, type ViewMode } from "./MemoryToolbar";
import { MemoryBreadcrumbs, type BreadcrumbItem } from "./MemoryBreadcrumbs";
import { MemoryFilters, type MemoryFiltersState } from "./MemoryFilters";
import { MemoryGrid } from "./MemoryGrid";
import { MemoryList } from "./MemoryList";
import { MemoryTimeline } from "./MemoryTimeline";

export type ExplorerView = "recent" | "pinned" | "explorer" | "knowledge" | "artifacts" | "people" | "browser" | "voice" | "vision" | "collections" | "tags" | "timeline";

export interface MemoryExplorerProps extends Omit<HTMLAttributes<HTMLDivElement>, "onSelect"> {
  view: ExplorerView;
  searchQuery?: string;
  onSelect?: (node: MemoryNodeType) => void;
  selectedNodeId?: string;
}

const viewToSuperType: Partial<Record<ExplorerView, NodeSuperType>> = {
  knowledge: "knowledge",
  artifacts: "artifact",
  people: "entity",
};

const viewToTypes: Partial<Record<ExplorerView, readonly string[]>> = {
  browser: [NodeTypeConstants.BROWSER_SESSION, NodeTypeConstants.BROWSER_PAGE, NodeTypeConstants.BROWSER_BOOKMARK],
  voice: [NodeTypeConstants.VOICE_SESSION, NodeTypeConstants.VOICE_COMMAND],
  vision: [NodeTypeConstants.VISION_CAPTURE, NodeTypeConstants.VISION_ANNOTATION],
  collections: [NodeTypeConstants.COLLECTION],
  tags: [NodeTypeConstants.TAG],
};

const viewLabels: Record<ExplorerView, string> = {
  recent: "Recent",
  pinned: "Pinned",
  explorer: "Explorer",
  knowledge: "Knowledge",
  artifacts: "Artifacts",
  people: "People",
  browser: "Browser",
  voice: "Voice",
  vision: "Vision",
  collections: "Collections",
  tags: "Tags",
  timeline: "Timeline",
};

export function MemoryExplorer({
  view,
  searchQuery,
  onSelect,
  selectedNodeId,
  className = "",
  ...rest
}: MemoryExplorerProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("grid");
  const [sortField, setSortField] = useState<SortField>("updatedAt");
  const [sortOrder, setSortOrder] = useState<SortOrder>("desc");
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState<MemoryFiltersState>({
    superTypes: [],
    statuses: [],
    tags: [],
    pinned: undefined,
    dateFrom: undefined,
    dateTo: undefined,
  });

  const store = useMemo(() => getMemoryStore(), []);

  const nodes = useMemo(() => {
    const allNodes = store.graph.getAllNodes();
    let filtered: readonly MemoryNodeType[] = allNodes;

    if (searchQuery) {
      const result = store.query.searchByKeyword(searchQuery);
      filtered = result.nodes;
    }

    if (view === "recent") {
      filtered = store.selectors.getRecentNodes(100);
    } else if (view === "pinned") {
      filtered = store.selectors.getPinnedNodes();
    } else if (view === "timeline") {
      filtered = store.selectors.getRecentNodes(200);
      return filtered;
    } else if (view === "explorer") {
      filtered = allNodes;
    } else {
      const superType = viewToSuperType[view];
      if (superType) {
        filtered = store.selectors.getNodesBySuperType(superType);
      }
      const types = viewToTypes[view];
      if (types) {
        filtered = filtered.filter((n) => types.includes(n.type) || types.includes(n.subtype));
      }
    }

    if (filters.superTypes.length > 0) {
      filtered = filtered.filter((n) =>
        filters.superTypes.includes(n.type as NodeSuperType)
      );
    }
    if (filters.statuses.length > 0) {
      filtered = filtered.filter((n) => filters.statuses.includes(n.status));
    }
    if (filters.tags.length > 0) {
      filtered = filtered.filter((n) =>
        filters.tags.some((t) => n.tags.includes(t))
      );
    }
    if (filters.pinned === true) {
      filtered = filtered.filter((n) => n.pinned);
    }

    const sorted = [...filtered].sort((a, b) => {
      const field = sortField as keyof MemoryNodeType;
      const aVal = a[field] ?? 0;
      const bVal = b[field] ?? 0;
      if (typeof aVal === "string" && typeof bVal === "string") {
        return sortOrder === "desc"
          ? bVal.localeCompare(aVal)
          : aVal.localeCompare(bVal);
      }
      return sortOrder === "desc"
        ? (bVal as number) - (aVal as number)
        : (aVal as number) - (bVal as number);
    });

    return sorted;
  }, [store, view, searchQuery, sortField, sortOrder, filters]);

  const breadcrumbs = useMemo((): BreadcrumbItem[] => {
    const items: BreadcrumbItem[] = [
      { label: "Memory", id: "memory" },
      { label: viewLabels[view], id: view },
    ];
    return items;
  }, [view]);

  const handleSortChange = useCallback((field: SortField, order: SortOrder) => {
    setSortField(field);
    setSortOrder(order);
  }, []);

  const availableTags = useMemo(() => {
    const allNodes = store.graph.getAllNodes();
    const tagSet = new Set<string>();
    allNodes.forEach((n) => n.tags.forEach((t) => tagSet.add(t)));
    return [...tagSet];
  }, [store]);

  const classes = ["mw-content", className].filter(Boolean).join(" ");

  return (
    <div className={classes} role="region" aria-label={viewLabels[view]} {...rest}>
      <MemoryToolbar
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        sortField={sortField}
        sortOrder={sortOrder}
        onSortChange={handleSortChange}
        totalCount={nodes.length}
        showFilters={showFilters}
        onToggleFilters={() => setShowFilters(!showFilters)}
      />

      <MemoryBreadcrumbs items={breadcrumbs} />

      {showFilters && (
        <MemoryFilters
          filters={filters}
          onChange={setFilters}
          availableTags={availableTags}
        />
      )}

      {view === "timeline" ? (
        <div className="mw-explorer">
          <MemoryTimeline nodes={nodes} onSelect={onSelect} />
        </div>
      ) : viewMode === "grid" ? (
        <div className="mw-explorer">
          <MemoryGrid
            nodes={nodes}
            selectedId={selectedNodeId}
            onSelect={onSelect}
          />
        </div>
      ) : (
        <div className="mw-explorer">
          <MemoryList
            nodes={nodes}
            selectedId={selectedNodeId}
            onSelect={onSelect}
          />
        </div>
      )}
    </div>
  );
}

export { viewLabels };
