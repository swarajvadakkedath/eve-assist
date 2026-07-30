import { useState, useEffect } from "react";
import { fetchApi } from "../../services/api";
import VoiceSettingsPanel from "../voice/VoiceSettingsPanel";
import VisionSettings from "../vision/VisionSettings";
import type { CommercialPolicy } from "../providers/types";
import { COMMERCIAL_POLICY_OPTIONS } from "../providers/types";

interface SettingsPanelProps {
  onClose: () => void;
}

function SettingsAITab() {
  const [policy, setPolicy] = useState<CommercialPolicy>("allow_paid");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [showPaidConfirm, setShowPaidConfirm] = useState(false);
  const [pendingPolicy, setPendingPolicy] = useState<CommercialPolicy | null>(null);

  useEffect(() => {
    fetchApi("/routing/commercial-policy")
      .then((r) => r.json())
      .then((data) => {
        setPolicy(data.policy || "allow_paid");
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const handleChange = async (newPolicy: CommercialPolicy) => {
    // If switching TO allow_paid from a more restrictive policy, show confirmation
    if (newPolicy === "allow_paid" && policy !== "allow_paid") {
      setPendingPolicy(newPolicy);
      setShowPaidConfirm(true);
      return;
    }
    await savePolicy(newPolicy);
  };

  const savePolicy = async (newPolicy: CommercialPolicy) => {
    setSaving(true);
    try {
      await fetchApi("/routing/commercial-policy", {
        method: "PUT",
        body: JSON.stringify({ policy: newPolicy }),
      });
      setPolicy(newPolicy);
    } catch (err) {
      console.error("Failed to save commercial policy", err);
    } finally {
      setSaving(false);
    }
  };

  const confirmPaid = () => {
    if (pendingPolicy) {
      savePolicy(pendingPolicy);
    }
    setShowPaidConfirm(false);
    setPendingPolicy(null);
  };

  const cancelPaid = () => {
    setShowPaidConfirm(false);
    setPendingPolicy(null);
  };

  if (loading) {
    return <div className="loading-skeleton">Loading AI settings...</div>;
  }

  const currentOption = COMMERCIAL_POLICY_OPTIONS.find(o => o.value === policy);

  return (
    <div className="pr-settings-ai">
      <h3>Routing Cost Policy</h3>
      <p className="pr-settings-ai-description">
        Control which AI routes Eve may use. This affects all conversations unless overridden per-conversation.
      </p>

      <div className="pr-settings-ai-policy-selector">
        {COMMERCIAL_POLICY_OPTIONS.map((opt) => (
          <label
            key={opt.value}
            className={`pr-settings-ai-policy-option ${policy === opt.value ? "selected" : ""}`}
          >
            <input
              type="radio"
              name="commercial-policy"
              value={opt.value}
              checked={policy === opt.value}
              onChange={() => handleChange(opt.value)}
              disabled={saving}
            />
            <div className="pr-settings-ai-policy-content">
              <span className="pr-settings-ai-policy-label">{opt.label}</span>
              <span className="pr-settings-ai-policy-desc">{opt.description}</span>
            </div>
          </label>
        ))}
      </div>

      {policy === "allow_paid" && (
        <div className="pr-settings-ai-paid-notice">
          Paid models may be selected when required. This can incur charges on configured provider accounts.
        </div>
      )}

      <button
        className="btn btn-primary"
        style={{ marginTop: 16, padding: "10px 24px", fontSize: 14 }}
        onClick={() => {
          window.dispatchEvent(new CustomEvent("aios:open-providers"));
        }}
      >
        Open Provider Manager
      </button>

      {showPaidConfirm && (
        <div className="pr-settings-ai-confirm-overlay" onClick={cancelPaid}>
          <div className="pr-settings-ai-confirm-dialog" onClick={(e) => e.stopPropagation()}>
            <h4>Allow paid AI routes?</h4>
            <p>
              Eve may use models that generate charges on configured provider accounts
              when free or included routes cannot satisfy a request.
            </p>
            <div className="pr-settings-ai-confirm-actions">
              <button className="btn btn-secondary" onClick={cancelPaid}>Cancel</button>
              <button className="btn btn-primary" onClick={confirmPaid}>Allow Paid Routes</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function SettingsPanel({ onClose }: SettingsPanelProps) {
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("general");

  useEffect(() => {
    fetchApi("/desktop/settings")
      .then((r) => r.json())
      .then((data) => setSettings(data))
      .catch((err) => {
        console.error("Failed to load settings:", err);
        setError("Failed to load settings");
      })
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    await fetchApi("/desktop/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ settings }),
    });
    setSaving(false);
    onClose();
  };

  const update = (path: string, value: any) => {
    setSettings((prev: any) => {
      if (!prev) return prev;
      const keys = path.split(".");
      const result = { ...prev };
      let target = result;
      for (let i = 0; i < keys.length - 1; i++) {
        target[keys[i]] = { ...target[keys[i]] };
        target = target[keys[i]];
      }
      target[keys[keys.length - 1]] = value;
      return result;
    });
  };

  return (
    <div className="settings-panel-overlay" onClick={onClose}>
      <div className="settings-panel settings-panel-wide" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Settings</h2>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>
        {loading && (
          <div className="settings-body" style={{ textAlign: "center", padding: 40, color: "var(--text-secondary)" }}>
            Loading settings...
          </div>
        )}
        {error && (
          <div className="settings-body" style={{ textAlign: "center", padding: 40, color: "var(--text-danger, #ef4444)" }}>
            {error}
            <br />
            <button className="btn btn-secondary" style={{ marginTop: 12 }} onClick={() => window.location.reload()}>
              Reload
            </button>
          </div>
        )}
        {!loading && !error && settings && (
        <>
        <div className="settings-tabs">
          {["general", "voice", "vision", "ai", "shortcuts", "notifications", "startup", "privacy"].map((tab) => (
            <button
              key={tab}
              className={`settings-tab ${activeTab === tab ? "active" : ""}`}
              onClick={() => setActiveTab(tab)}
            >
              {tab.charAt(0).toUpperCase() + tab.slice(1)}
            </button>
          ))}
        </div>
        <div className="settings-body">
          {activeTab === "general" && (
            <>
              <div className="setting-group">
                <label>Theme</label>
                <select value={settings?.ui?.theme || "dark"} onChange={(e) => update("ui.theme", e.target.value)}>
                  <option value="light">Light</option>
                  <option value="dark">Dark</option>
                  <option value="system">System</option>
                </select>
              </div>
              <div className="setting-group">
                <label>Accent Color</label>
                <input type="color" value={settings?.ui?.accent_color || "#6366f1"} onChange={(e) => update("ui.accent_color", e.target.value)} />
              </div>
            </>
          )}
          {activeTab === "voice" && (
            <VoiceSettingsPanel />
          )}
          {activeTab === "vision" && (
            <VisionSettings />
          )}
          {activeTab === "ai" && (
            <SettingsAITab />
          )}
          {activeTab === "shortcuts" && (
            <>
              <div className="setting-group">
                <label>Toggle Eve</label>
                <input type="text" value={settings?.global_shortcuts?.toggle_eve || "ctrl+space"} onChange={(e) => update("global_shortcuts.toggle_eve", e.target.value)} />
              </div>
              <div className="setting-group">
                <label>Quick Command</label>
                <input type="text" value={settings?.global_shortcuts?.quick_command || "ctrl+shift+space"} onChange={(e) => update("global_shortcuts.quick_command", e.target.value)} />
              </div>
              <div className="setting-group">
                <label>New Conversation</label>
                <input type="text" value={settings?.global_shortcuts?.new_conversation || "ctrl+alt+e"} onChange={(e) => update("global_shortcuts.new_conversation", e.target.value)} />
              </div>
            </>
          )}
          {activeTab === "notifications" && (
            <>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.notifications?.permission_requests ?? true} onChange={(e) => update("notifications.permission_requests", e.target.checked)} />
                  Permission Requests
                </label>
              </div>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.notifications?.task_completed ?? true} onChange={(e) => update("notifications.task_completed", e.target.checked)} />
                  Task Completed
                </label>
              </div>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.notifications?.ai_finished ?? true} onChange={(e) => update("notifications.ai_finished", e.target.checked)} />
                  AI Finished
                </label>
              </div>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.notifications?.plugin_installed ?? true} onChange={(e) => update("notifications.plugin_installed", e.target.checked)} />
                  Plugin Installed
                </label>
              </div>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.notifications?.update_available ?? true} onChange={(e) => update("notifications.update_available", e.target.checked)} />
                  Update Available
                </label>
              </div>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.notifications?.warnings ?? true} onChange={(e) => update("notifications.warnings", e.target.checked)} />
                  Warnings
                </label>
              </div>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.notifications?.errors ?? true} onChange={(e) => update("notifications.errors", e.target.checked)} />
                  Errors
                </label>
              </div>
            </>
          )}
          {activeTab === "startup" && (
            <>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.startup?.launch_at_startup ?? false} onChange={(e) => update("startup.launch_at_startup", e.target.checked)} />
                  Launch at Windows Startup
                </label>
              </div>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.startup?.start_minimized ?? false} onChange={(e) => update("startup.start_minimized", e.target.checked)} />
                  Start Minimized
                </label>
              </div>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.startup?.background_mode ?? false} onChange={(e) => update("startup.background_mode", e.target.checked)} />
                  Background Mode
                </label>
              </div>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.startup?.minimize_to_tray_on_close ?? true} onChange={(e) => update("startup.minimize_to_tray_on_close", e.target.checked)} />
                  Minimize to Tray on Close
                </label>
              </div>
            </>
          )}
          {activeTab === "privacy" && (
            <>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.privacy?.analytics_enabled ?? false} onChange={(e) => update("privacy.analytics_enabled", e.target.checked)} />
                  Enable Analytics
                </label>
              </div>
              <div className="setting-group">
                <label className="setting-toggle">
                  <input type="checkbox" checked={settings?.privacy?.crash_reporting ?? true} onChange={(e) => update("privacy.crash_reporting", e.target.checked)} />
                  Crash Reporting
                </label>
              </div>
            </>
          )}
        </div>
        <div className="settings-footer">
          <button className="btn btn-secondary" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
        </>
        )}
      </div>
    </div>
  );
}
