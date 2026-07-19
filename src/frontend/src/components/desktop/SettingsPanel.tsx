import { useState, useEffect } from "react";

interface SettingsPanelProps {
  onClose: () => void;
}

export default function SettingsPanel({ onClose }: SettingsPanelProps) {
  const [settings, setSettings] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [activeTab, setActiveTab] = useState("general");

  useEffect(() => {
    fetch("/api/v1/desktop/settings")
      .then((r) => r.json())
      .then((data) => setSettings(data))
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async () => {
    if (!settings) return;
    setSaving(true);
    await fetch("/api/v1/desktop/settings", {
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

  if (!settings) return null;

  return (
    <div className="settings-panel-overlay" onClick={onClose}>
      <div className="settings-panel settings-panel-wide" onClick={(e) => e.stopPropagation()}>
        <div className="settings-header">
          <h2>Settings</h2>
          <button className="btn-close" onClick={onClose}>×</button>
        </div>
        <div className="settings-tabs">
          {["general", "ai", "shortcuts", "notifications", "startup", "privacy"].map((tab) => (
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
          {activeTab === "ai" && (
            <>
              <div className="setting-group">
                <label>AI Provider</label>
                <select value={settings?.ai?.provider || "openai"} onChange={(e) => update("ai.provider", e.target.value)}>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="local">Local</option>
                </select>
              </div>
              <div className="setting-group">
                <label>AI Model</label>
                <input type="text" value={settings?.ai?.model || "gpt-4o"} onChange={(e) => update("ai.model", e.target.value)} />
              </div>
            </>
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
      </div>
    </div>
  );
}
