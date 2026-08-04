import { useState, useCallback } from "react";
import { useAioStore } from "./AioStore";
import { fetchErrorReport, clearErrors } from "./aioApi";
import type { AioErrorEvent } from "./aioTypes";

const SEVERITY_COLORS: Record<string, string> = {
  INFO: "#6b7280",
  LOW: "#3b82f6",
  MEDIUM: "#f59e0b",
  HIGH: "#ef4444",
  CRITICAL: "#dc2626",
};

const CATEGORY_ICONS: Record<string, string> = {
  PROVIDER: "🔗",
  ROUTING: "🧭",
  NETWORK: "🌐",
  VOICE: "🎤",
  VISION: "👁",
  MEMORY: "🧠",
  WORKSPACE: "📂",
  FILE_SEARCH: "🔍",
  OCR: "📄",
  PLUGIN: "🧩",
  TOOL_EXECUTION: "🛠",
  DATABASE: "💾",
  AUTHENTICATION: "🔑",
  PERMISSION: "🔒",
  CONFIGURATION: "⚙",
  API: "📡",
  TIMEOUT: "⏱",
  STREAMING: "📡",
  RATE_LIMIT: "🚦",
  INTERNAL_BUG: "🐛",
  UNKNOWN: "❓",
};

export default function RecoveryView() {
  const { errors, errorStats, errorTimeline } = useAioStore();
  const [selectedError, setSelectedError] = useState<AioErrorEvent | null>(null);
  const [filterCategory, setFilterCategory] = useState<string>("");
  const [filterSeverity, setFilterSeverity] = useState<string>("");
  const [showCopied, setShowCopied] = useState(false);

  const handleCopyReport = useCallback(async (fmt: "markdown" | "json" | "plain") => {
    if (!selectedError) return;
    try {
      const result = await fetchErrorReport(selectedError.error_id, fmt);
      await navigator.clipboard.writeText(result.report);
      setShowCopied(true);
      setTimeout(() => setShowCopied(false), 2000);
    } catch {
      // clipboard may be unavailable
    }
  }, [selectedError]);

  const handleClear = useCallback(async () => {
    if (!confirm("Clear all error history?")) return;
    await clearErrors();
    window.location.reload();
  }, []);

  const filteredErrors = errors.filter((e) => {
    if (filterCategory && e.category !== filterCategory) return false;
    if (filterSeverity && e.severity !== filterSeverity) return false;
    return true;
  });

  return (
    <div className="aio-recovery">
      {/* Stats Grid */}
      <div className="aio-stats-grid">
        <StatCard label="Total Errors" value={errorStats?.total ?? errors.length} color="#ef4444" />
        <StatCard label="Resolved" value={errorStats?.resolved ?? 0} color="#22c55e" />
        <StatCard label="Recovery Rate" value={`${errorStats?.recovery_success_rate ?? 0}%`} color="#3b82f6" />
        <StatCard label="Auto Recoveries" value={errorStats?.auto_recoveries?.attempted ?? 0} color="#8b5cf6" />
      </div>

      {/* Filters */}
      <div className="aio-recovery-filters">
        <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}>
          <option value="">All Categories</option>
          {Object.keys(CATEGORY_ICONS).map((cat) => (
            <option key={cat} value={cat}>{CATEGORY_ICONS[cat]} {cat}</option>
          ))}
        </select>
        <select value={filterSeverity} onChange={(e) => setFilterSeverity(e.target.value)}>
          <option value="">All Severities</option>
          {Object.keys(SEVERITY_COLORS).map((sev) => (
            <option key={sev} value={sev}>{sev}</option>
          ))}
        </select>
        <button className="aio-btn aio-btn-danger" onClick={handleClear}>Clear History</button>
      </div>

      <div className="aio-recovery-layout">
        {/* Error List */}
        <div className="aio-recovery-list">
          <h3 className="aio-section-title">Recent Errors ({filteredErrors.length})</h3>
          {filteredErrors.length === 0 && <p className="aio-empty">No errors recorded</p>}
          {filteredErrors.map((err) => (
            <div
              key={err.error_id}
              className={`aio-recovery-item ${selectedError?.error_id === err.error_id ? "selected" : ""}`}
              onClick={() => setSelectedError(err)}
            >
              <div className="aio-recovery-item-header">
                <span className="aio-recovery-category">{CATEGORY_ICONS[err.category] ?? "❓"} {err.category}</span>
                <span className="aio-recovery-severity" style={{ color: SEVERITY_COLORS[err.severity] }}>
                  {err.severity}
                </span>
              </div>
              <div className="aio-recovery-item-message">{err.message}</div>
              <div className="aio-recovery-item-meta">
                {err.provider && <span className="aio-pill">{err.provider}</span>}
                {err.model && <span className="aio-pill">{err.model}</span>}
                <span className="aio-recovery-time">{new Date(err.timestamp).toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Error Detail */}
        <div className="aio-recovery-detail">
          {selectedError ? (
            <>
              <h3 className="aio-section-title">Error Details</h3>
              <div className="aio-recovery-detail-card">
                <div className="aio-recovery-detail-header">
                  <span className="aio-recovery-category">{CATEGORY_ICONS[selectedError.category] ?? "❓"} {selectedError.category}</span>
                  <span className="aio-recovery-severity" style={{ color: SEVERITY_COLORS[selectedError.severity] }}>
                    {selectedError.severity}
                  </span>
                </div>
                <p className="aio-recovery-message">{selectedError.message}</p>
                {selectedError.likely_cause && (
                  <div className="aio-recovery-cause">
                    <strong>Likely Cause:</strong> {selectedError.likely_cause}
                  </div>
                )}
                {selectedError.root_cause && (
                  <div className="aio-recovery-cause">
                    <strong>Root Cause:</strong> {selectedError.root_cause}
                  </div>
                )}
                {selectedError.recovery_suggestions.length > 0 && (
                  <div className="aio-recovery-suggestions">
                    <strong>What EVE can do:</strong>
                    <ul>
                      {selectedError.recovery_suggestions.map((s, i) => (
                        <li key={i}>✓ {s}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <div className="aio-recovery-meta-grid">
                  {selectedError.provider && <div><strong>Provider:</strong> {selectedError.provider}</div>}
                  {selectedError.model && <div><strong>Model:</strong> {selectedError.model}</div>}
                  {selectedError.tool && <div><strong>Tool:</strong> {selectedError.tool}</div>}
                  {selectedError.http_status && <div><strong>HTTP Status:</strong> {selectedError.http_status}</div>}
                  {selectedError.exception_type && <div><strong>Exception:</strong> {selectedError.exception_type}</div>}
                  {selectedError.duration && <div><strong>Duration:</strong> {Math.round(selectedError.duration)}ms</div>}
                  {selectedError.recoverable !== undefined && <div><strong>Recoverable:</strong> {selectedError.recoverable ? "Yes" : "No"}</div>}
                  {selectedError.auto_recovery_attempted && (
                    <div><strong>Auto Recovery:</strong> {selectedError.recovery_result ?? "attempted"}</div>
                  )}
                </div>
                {selectedError.stack_trace && (
                  <details className="aio-recovery-stacktrace">
                    <summary>Technical Details</summary>
                    <pre>{selectedError.stack_trace}</pre>
                  </details>
                )}
                <div className="aio-recovery-actions">
                  <button className="aio-btn" onClick={() => handleCopyReport("markdown")}>
                    {showCopied ? "Copied!" : "Copy Markdown"}
                  </button>
                  <button className="aio-btn" onClick={() => handleCopyReport("json")}>Copy JSON</button>
                  <button className="aio-btn" onClick={() => handleCopyReport("plain")}>Copy Plain Text</button>
                </div>
              </div>
            </>
          ) : (
            <p className="aio-empty">Select an error to view details</p>
          )}
        </div>
      </div>

      {/* Timeline */}
      {errorTimeline.length > 0 && (
        <div className="aio-recovery-timeline">
          <h3 className="aio-section-title">Error Timeline</h3>
          <div className="aio-timeline-list">
            {errorTimeline.slice(0, 50).map((evt, i) => (
              <div key={i} className="aio-timeline-item">
                <span className="aio-timeline-dot" style={{ backgroundColor: SEVERITY_COLORS[evt.severity] ?? "#6b7280" }} />
                <span className="aio-timeline-time">{new Date(evt.timestamp).toLocaleTimeString()}</span>
                <span className="aio-timeline-type">[{evt.type}]</span>
                <span className="aio-timeline-message">{evt.message}</span>
                {evt.provider && <span className="aio-pill">{evt.provider}</span>}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, color }: { label: string; value: string | number; color: string }) {
  return (
    <div className="aio-stat-card" style={{ borderTopColor: color }}>
      <div className="aio-stat-value" style={{ color }}>{value}</div>
      <div className="aio-stat-label">{label}</div>
    </div>
  );
}
