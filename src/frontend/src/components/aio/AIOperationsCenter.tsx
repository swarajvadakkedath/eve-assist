import { useState, useEffect } from "react";
import { AIO_TABS } from "./aioTypes";
import type { AioTabId } from "./aioTypes";
import { aioStore } from "./AioStore";
import { useAioStore } from "./AioStore";
import DashboardView from "./DashboardView";
import ProvidersView from "./ProvidersView";
import ModelsView from "./ModelsView";
import SmartRouterView from "./SmartRouterView";
import HealthView from "./HealthView";
import ActivityView from "./ActivityView";
import AioSettingsView from "./AioSettingsView";
import "./ai-operations.css";

function formatRelativeTime(ts: number): string {
  if (ts === 0) return "never";
  const diff = Date.now() - ts;
  if (diff < 60_000) return `${Math.round(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h ago`;
  return `${Math.round(diff / 86_400_000)}d ago`;
}

interface AIOperationsCenterProps {
  onClose?: () => void;
}

const VIEW_MAP: Record<AioTabId, React.FC> = {
  dashboard: DashboardView,
  providers: ProvidersView,
  models: ModelsView,
  smartrouter: SmartRouterView,
  health: HealthView,
  activity: ActivityView,
  settings: AioSettingsView,
};

function AIOperationsCenter({ onClose }: AIOperationsCenterProps) {
  const [activeTab, setActiveTab] = useState<AioTabId>("dashboard");
  const { loading, providers, lastRefresh } = useAioStore();

  useEffect(() => {
    aioStore.start();

    const handleAioTab = (e: Event) => {
      const tab = (e as CustomEvent).detail;
      if (typeof tab === "string") setActiveTab(tab as AioTabId);
    };
    window.addEventListener("aios:aio-tab", handleAioTab);

    return () => {
      aioStore.stop();
      window.removeEventListener("aios:aio-tab", handleAioTab);
    };
  }, []);

  const ViewComponent = VIEW_MAP[activeTab];

  return (
    <div className="aio-page">
      <div className="aio-header">
        <div className="aio-title">
          <div className="aio-status-dot" />
          AI Operations Center
        </div>
        <div className="aio-header-meta">
          <span>Last refresh: {formatRelativeTime(lastRefresh)}</span>
          <button className="aio-close-btn" onClick={onClose ?? (() => window.dispatchEvent(new CustomEvent("aios:switch-workspace", { detail: "conversation" })))}>
            ✕
          </button>
        </div>
      </div>

      <nav className="aio-nav">
        {AIO_TABS.map((tab) => (
          <button
            key={tab.id}
            className={`aio-nav-tab${activeTab === tab.id ? " active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            <span>{tab.icon}</span>
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="aio-body">
        {loading && providers.length === 0 ? (
          <div className="aio-loading">
            <div className="aio-spinner" />
            <span>Loading operations center…</span>
          </div>
        ) : (
          <ViewComponent />
        )}
      </div>
    </div>
  );
}

export default AIOperationsCenter;
