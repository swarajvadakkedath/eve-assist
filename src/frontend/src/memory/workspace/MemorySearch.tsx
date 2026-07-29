import { useState, useCallback, useMemo, useId, useEffect, useRef } from "react";
import type { HTMLAttributes } from "react";
import type { MemoryNode, SearchQuery, SearchResult } from "@/memory/core";
import { getMemoryStore } from "@/memory/core";
import { MemoryList } from "./MemoryList";

export interface MemorySearchProps extends HTMLAttributes<HTMLDivElement> {
  onSelect?: (node: MemoryNode) => void;
  onClose?: () => void;
  placeholder?: string;
}

export function MemorySearch({
  onSelect,
  onClose,
  placeholder = "Search memory...",
  className = "",
  ...rest
}: MemorySearchProps) {
  const inputId = useId();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult | null>(null);
  const [loading, setLoading] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout>>();

  const executeSearch = useCallback((keyword: string) => {
    if (!keyword.trim()) {
      setResults(null);
      return;
    }

    setLoading(true);
    const store = getMemoryStore();
    const searchQuery: SearchQuery = {
      keyword: keyword.trim(),
      options: { limit: 50, sortField: "updatedAt", sortOrder: "desc" },
    };

    const searchResults = store.query.execute(searchQuery);
    setResults(searchResults);
    setLoading(false);
  }, []);

  const handleInputChange = useCallback((value: string) => {
    setQuery(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => executeSearch(value), 200);
  }, [executeSearch]);

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const classes = ["mw-search", className].filter(Boolean).join(" ");

  return (
    <div className={classes} role="search" aria-label="Memory search" {...rest}>
      <div className="mw-search-input-wrapper">
        <label htmlFor={inputId} className="sr-only">Search memory</label>
        <input
          id={inputId}
          className="pr-input"
          type="search"
          placeholder={placeholder}
          value={query}
          onChange={(e) => handleInputChange(e.target.value)}
          autoFocus
          aria-describedby={results ? "mw-search-results-count" : undefined}
          style={{ width: "100%", paddingRight: "32px" }}
        />
        {query && (
          <button
            className="pr-btn pr-btn-ghost pr-btn-sm"
            onClick={() => { setQuery(""); setResults(null); }}
            aria-label="Clear search"
            style={{ position: "absolute", right: "4px", top: "50%", transform: "translateY(-50%)" }}
          >
            ✕
          </button>
        )}
      </div>

      {loading && (
        <div className="mw-search-empty" role="status" aria-live="polite">
          Searching...
        </div>
      )}

      {results && !loading && (
        <>
          <p id="mw-search-results-count" className="sr-only">
            {results.total} result{results.total !== 1 ? "s" : ""} found
          </p>
          {results.nodes.length === 0 ? (
            <div className="mw-search-empty" role="status">
              No results found for "{query}"
            </div>
          ) : (
            <div className="mw-search-results">
              <div style={{ fontSize: "var(--text-xs)", color: "var(--color-text-muted)", marginBottom: "var(--space-2)" }}>
                {results.total} result{results.total !== 1 ? "s" : ""}
              </div>
              <MemoryList
                nodes={results.nodes}
                onSelect={onSelect}
              />
            </div>
          )}
        </>
      )}

      {!query && !results && (
        <div className="mw-search-empty" role="status">
          Type to search memory nodes
        </div>
      )}
    </div>
  );
}
