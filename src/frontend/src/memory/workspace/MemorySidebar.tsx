import { useState, useCallback } from "react";
import type { HTMLAttributes } from "react";

export interface SidebarSection {
  id: string;
  label: string;
  icon: string;
  count?: number;
}

export interface MemorySidebarProps extends HTMLAttributes<HTMLDivElement> {
  sections: readonly SidebarSection[];
  activeSection: string;
  onSectionChange: (sectionId: string) => void;
  onSearch?: (query: string) => void;
  searchQuery?: string;
}

const defaultSections: SidebarSection[] = [
  { id: "recent", label: "Recent", icon: "🕐" },
  { id: "pinned", label: "Pinned", icon: "📌" },
  { id: "explorer", label: "Explorer", icon: "🗂" },
  { id: "knowledge", label: "Knowledge", icon: "🧠" },
  { id: "artifacts", label: "Artifacts", icon: "📄" },
  { id: "people", label: "People", icon: "👤" },
  { id: "browser", label: "Browser", icon: "🌐" },
  { id: "voice", label: "Voice", icon: "🎤" },
  { id: "vision", label: "Vision", icon: "📷" },
  { id: "collections", label: "Collections", icon: "📁" },
  { id: "tags", label: "Tags", icon: "🏷" },
  { id: "timeline", label: "Timeline", icon: "📅" },
];

export function MemorySidebar({
  sections = defaultSections,
  activeSection,
  onSectionChange,
  onSearch,
  searchQuery = "",
  className = "",
  ...rest
}: MemorySidebarProps) {
  const [localSearch, setLocalSearch] = useState(searchQuery);

  const handleSearchChange = useCallback((value: string) => {
    setLocalSearch(value);
    onSearch?.(value);
  }, [onSearch]);

  const classes = ["mw-sidebar", className].filter(Boolean).join(" ");

  return (
    <aside className={classes} aria-label="Memory navigation" {...rest}>
      <div className="mw-sidebar-header">
        <input
          className="pr-input"
          type="search"
          placeholder="Search memory..."
          value={localSearch}
          onChange={(e) => handleSearchChange(e.target.value)}
          aria-label="Search memory"
          style={{ width: "100%" }}
        />
      </div>

      <nav className="mw-sidebar-nav" aria-label="Memory sections">
        {sections.map((section) => (
          <div
            key={section.id}
            className={`mw-sidebar-item${activeSection === section.id ? " active" : ""}`}
            role="button"
            tabIndex={0}
            aria-current={activeSection === section.id ? "page" : undefined}
            onClick={() => onSectionChange(section.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault();
                onSectionChange(section.id);
              }
            }}
          >
            <span aria-hidden="true">{section.icon}</span>
            <span>{section.label}</span>
            {section.count !== undefined && (
              <span className="mw-sidebar-item-count" aria-label={`${section.count} items`}>
                {section.count}
              </span>
            )}
          </div>
        ))}
      </nav>
    </aside>
  );
}
