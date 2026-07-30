import { useState, useEffect, useMemo } from "react";
import { fetchApi } from "../../services/api";
import type { Model } from "./types";

interface ModelSelectorProps {
  providerId: string;
  value: string;
  onChange: (modelId: string) => void;
  disabled?: boolean;
}

export default function ModelSelector({
  providerId,
  value,
  onChange,
  disabled,
}: ModelSelectorProps) {
  const [models, setModels] = useState<Model[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState<Record<string, boolean>>({});

  useEffect(() => {
    if (!providerId) return;
    setLoading(true);
    fetchApi(`/providers/${providerId}/models`)
      .then((r) => r.json())
      .then((data) => {
        setModels((data.models || []).filter((m: Model) => m.enabled !== false));
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, [providerId]);

  const filteredModels = useMemo(() => {
    let result = models;
    const q = search.toLowerCase();
    if (q) {
      result = result.filter(
        (m) =>
          m.id.toLowerCase().includes(q) ||
          m.displayName.toLowerCase().includes(q)
      );
    }
    if (filters.free) result = result.filter((m) => m.isFree);
    if (filters.vision) result = result.filter((m) => m.supportsVision);
    if (filters.reasoning) result = result.filter((m) => m.supportsReasoning);
    if (filters.recommended) result = result.filter((m) => m.recommended);
    if (filters.largeContext) result = result.filter((m) => (m.contextLength || 0) >= 128000);
    if (filters.fast) result = result.filter((m) => typeof m.speed === "number" && m.speed >= 8);
    return result;
  }, [models, search, filters]);

  const toggleFilter = (key: string) => {
    setFilters((prev) => ({ ...prev, [key]: !prev[key] }));
  };

  const filterButtons = [
    { key: "free", label: "Free" },
    { key: "vision", label: "Vision" },
    { key: "reasoning", label: "Reasoning" },
    { key: "recommended", label: "Recommended" },
    { key: "largeContext", label: "128K+" },
    { key: "fast", label: "Fast" },
  ];

  return (
    <div className="ms-wrapper">
      <label className="ms-label">Model</label>
      <div className="ms-filters">
        {filterButtons.map((fb) => (
          <button
            key={fb.key}
            className={`ms-filter-btn ${filters[fb.key] ? "ms-filter-active" : ""}`}
            onClick={() => toggleFilter(fb.key)}
          >
            {fb.label}
          </button>
        ))}
      </div>
      <div className="ms-search">
        <input
          type="text"
          placeholder="Search models..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="ms-search-input"
        />
      </div>
      {loading ? (
        <div className="ms-loading">Loading models...</div>
      ) : (
        <div className="ms-list">
          {filteredModels.map((m) => (
            <label
              key={m.id}
              className={`ms-item ${value === m.id ? "ms-item-selected" : ""}`}
            >
              <input
                type="radio"
                name="ms-model"
                checked={value === m.id}
                onChange={() => onChange(m.id)}
                disabled={disabled || m.deprecated}
              />
              <div className="ms-item-content">
                <span className="ms-item-name">
                  {m.displayName}
                  {m.recommended && <span className="ms-badge ms-badge-rec">Recommended</span>}
                  {m.isFree && <span className="ms-badge ms-badge-free">Free</span>}
                  {!m.isFree && m.costPer1kInput === 0 && m.costPer1kOutput === 0 && (
                    <span className="pr-commercial-badge local">Local</span>
                  )}
                  {!m.isFree && (m.costPer1kInput > 0 || m.costPer1kOutput > 0) && (
                    <span className="pr-commercial-badge paid">Paid</span>
                  )}
                  {m.deprecated && <span className="ms-badge ms-badge-dep">Deprecated</span>}
                </span>
                <span className="ms-item-detail">
                  {m.contextLength.toLocaleString()} ctx
                  {m.supportsVision && " \u{1F5BC}"}
                  {m.supportsReasoning && " \u{1F9E0}"}
                  {m.supportsFunctionCalling && " \u{2699}"}
                  {typeof m.speed === "number" && m.speed >= 8 && " \u{26A1}"}
                  {!m.isFree && (m.costPer1kInput > 0 || m.costPer1kOutput > 0) && (
                    <span className="ms-item-cost">
                      ${m.costPer1kInput.toFixed(2)}/${m.costPer1kOutput.toFixed(2)} per 1K
                    </span>
                  )}
                </span>
              </div>
            </label>
          ))}
          {filteredModels.length === 0 && (
            <div className="ms-empty">No models match your filters.</div>
          )}
        </div>
      )}
    </div>
  );
}
