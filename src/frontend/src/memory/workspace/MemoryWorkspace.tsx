"use client";

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import type { HTMLAttributes } from "react";
import type { MemoryNode } from "@/memory/core";
import { getMemoryStore } from "@/memory/core";
import { MemorySidebar, type SidebarSection } from "./MemorySidebar";
import { MemoryExplorer, type ExplorerView, viewLabels } from "./MemoryExplorer";
import { MemoryInspector } from "./MemoryInspector";
import { MemorySearch } from "./MemorySearch";
import "./memory-workspace.css";

export interface MemoryWorkspaceProps extends HTMLAttributes<HTMLDivElement> {
  sections?: readonly SidebarSection[];
  defaultView?: ExplorerView;
  showInspector?: boolean;
}

export function MemoryWorkspace({
  sections,
  defaultView = "recent",
  showInspector = true,
  className = "",
  ...rest
}: MemoryWorkspaceProps) {
  const [activeView, setActiveView] = useState<ExplorerView>(defaultView);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedNode, setSelectedNode] = useState<MemoryNode | null>(null);
  const [showSearch, setShowSearch] = useState(false);
  const storeRef = useRef(getMemoryStore());

  const stats = useMemo(() => {
    const s = storeRef.current.selectors.getStats();
    const allNodes = storeRef.current.graph.getAllNodes();
    return { ...s, total: s.total };
  }, []);

  const sectionsWithCounts = useMemo(() => {
    if (sections) return sections;
    const base: SidebarSection[] = [
      { id: "recent", label: "Recent", icon: "🕐" },
      { id: "pinned", label: "Pinned", icon: "📌", count: stats.pinned },
      { id: "explorer", label: "Explorer", icon: "🗂", count: stats.total },
      { id: "knowledge", label: "Knowledge", icon: "🧠", count: stats.bySuperType.knowledge },
      { id: "artifacts", label: "Artifacts", icon: "📄", count: stats.bySuperType.artifact },
      { id: "people", label: "People", icon: "👤", count: stats.bySuperType.entity },
      { id: "browser", label: "Browser", icon: "🌐" },
      { id: "voice", label: "Voice", icon: "🎤" },
      { id: "vision", label: "Vision", icon: "📷" },
      { id: "collections", label: "Collections", icon: "📁" },
      { id: "tags", label: "Tags", icon: "🏷" },
      { id: "timeline", label: "Timeline", icon: "📅", count: stats.active },
    ];
    return base;
  }, [sections, stats]);

  const handleSectionChange = useCallback((sectionId: string) => {
    if (sectionId === "search") {
      setShowSearch(true);
      return;
    }
    setActiveView(sectionId as ExplorerView);
    setSelectedNode(null);
    setShowSearch(false);
  }, []);

  const handleSelect = useCallback((node: MemoryNode) => {
    setSelectedNode(node);
  }, []);

  const handleSearchSelect = useCallback((node: MemoryNode) => {
    setSelectedNode(node);
    setShowSearch(false);
  }, []);

  const handleCloseInspector = useCallback(() => {
    setSelectedNode(null);
  }, []);

  const handlePin = useCallback((node: MemoryNode) => {
    const store = storeRef.current;
    store.updateNode(node.id, { pinned: !node.pinned } as Partial<MemoryNode>);
    setSelectedNode(null);
  }, []);

  const handleArchive = useCallback((node: MemoryNode) => {
    const store = storeRef.current;
    if (node.archived) {
      store.graph.restoreNode(node.id);
    } else {
      store.graph.archiveNode(node.id);
    }
    setSelectedNode(null);
  }, []);

  const handleDelete = useCallback((node: MemoryNode) => {
    const store = storeRef.current;
    store.deleteNode(node.id);
    setSelectedNode(null);
  }, []);

  const classes = ["mw-layout", className].filter(Boolean).join(" ");

  return (
    <div className={classes} {...rest}>
      <MemorySidebar
        sections={sectionsWithCounts}
        activeSection={showSearch ? "search" : activeView}
        onSectionChange={handleSectionChange}
        onSearch={setSearchQuery}
        searchQuery={searchQuery}
      />

      {showSearch ? (
        <div className="mw-content" role="region" aria-label="Search results">
          <MemorySearch onSelect={handleSearchSelect} onClose={() => setShowSearch(false)} />
        </div>
      ) : (
        <MemoryExplorer
          view={activeView}
          searchQuery={searchQuery}
          onSelect={handleSelect}
          selectedNodeId={selectedNode ? `${selectedNode.id.type}:${selectedNode.id.value}` : undefined}
        />
      )}

      {showInspector && selectedNode && (
        <MemoryInspector
          node={selectedNode}
          onClose={handleCloseInspector}
          actions={{ onPin: handlePin, onArchive: handleArchive, onDelete: handleDelete }}
        />
      )}
    </div>
  );
}
