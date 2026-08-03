import { useState } from "react";
import { useAioStore, aioStore } from "./AioStore";
import { setCommercialPolicy } from "./aioApi";

function formatRelativeTime(ts: number): string {
  if (ts === 0) return "never";
  const diff = Date.now() - ts;
  if (diff < 60_000) return `${Math.round(diff / 1000)}s ago`;
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h ago`;
  return `${Math.round(diff / 86_400_000)}d ago`;
}

function AioSettingsView() {
  const { policy, lastRefresh, lastHealthCheck } = useAioStore();
  const [savingPolicy, setSavingPolicy] = useState(false);

  async function handlePolicyChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const newPolicy = e.target.value;
    setSavingPolicy(true);
    try {
      await setCommercialPolicy(newPolicy);
      await aioStore.forceRefresh();
    } catch {
      // policy change failed, store state unchanged
    } finally {
      setSavingPolicy(false);
    }
  }

  return (
    <div>
      <div className="aio-section-title">AI Operations Settings</div>

      <div className="aio-settings-row">
        <div>
          <div className="aio-settings-label">Commercial Policy</div>
          <div className="aio-settings-desc">Controls which models can be routed to</div>
        </div>
        <select
          className="aio-select"
          value={policy}
          onChange={handlePolicyChange}
          disabled={savingPolicy}
        >
          <option value="free_only">Free Only</option>
          <option value="no_direct_paid">No Direct Paid</option>
          <option value="allow_paid">Allow Paid</option>
        </select>
      </div>

      <div className="aio-settings-row">
        <div>
          <div className="aio-settings-label">Health Check Interval</div>
          <div className="aio-settings-desc">How often provider health is verified</div>
        </div>
        <div style={{ fontSize: 13 }}>120 seconds</div>
      </div>

      <div className="aio-settings-row">
        <div>
          <div className="aio-settings-label">Model Refresh Interval</div>
          <div className="aio-settings-desc">How often model catalogs are refreshed</div>
        </div>
        <div style={{ fontSize: 13 }}>3600 seconds</div>
      </div>

      <div className="aio-settings-row">
        <div>
          <div className="aio-settings-label">Background Workers</div>
          <div className="aio-settings-desc">Scheduled background tasks</div>
        </div>
        <div style={{ fontSize: 13 }}>
          <div>Health monitor: active</div>
          <div>Model refresh: active</div>
        </div>
      </div>

      <div className="aio-settings-row">
        <div>
          <div className="aio-settings-label">Last Health Check</div>
          <div className="aio-settings-desc">Most recent provider health poll</div>
        </div>
        <div style={{ fontSize: 13 }}>{formatRelativeTime(lastHealthCheck)}</div>
      </div>

      <div className="aio-settings-row">
        <div>
          <div className="aio-settings-label">Last Model Refresh</div>
          <div className="aio-settings-desc">Most recent model catalog update</div>
        </div>
        <div style={{ fontSize: 13 }}>{formatRelativeTime(lastRefresh)}</div>
      </div>
    </div>
  );
}

export default AioSettingsView;
