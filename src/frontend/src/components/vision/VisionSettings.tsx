import { useEffect, useState } from "react";
import { api } from "../../services/api";

interface VisionSettingsData {
  provider: string;
  ocr_engine: string;
  capture_quality: number;
  privacy_filters: boolean;
  auto_redact: boolean;
  observation_mode: string;
}

interface Provider {
  id: string;
  name: string;
  capabilities: string[];
}

interface Monitor {
  id: number;
  name: string;
  width: number;
  height: number;
  is_primary: boolean;
}

export default function VisionSettings() {
  const [config, setConfig] = useState<VisionSettingsData | null>(null);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    loadSettings();
  }, []);

  const loadSettings = async () => {
    try {
      const [cfg, prov, mon] = await Promise.all([
        api.vision.config() as Promise<VisionSettingsData>,
        api.vision.providers() as Promise<{ providers: Provider[] }>,
        api.vision.monitors() as Promise<{ monitors: Monitor[] }>,
      ]);
      setConfig(cfg);
      setProviders(prov.providers);
      setMonitors(mon.monitors);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load settings");
    }
  };

  const handleSave = async () => {
    if (!config) return;
    setSaving(true);
    setSaved(false);
    try {
      await api.vision.updateConfig(config as unknown as Record<string, unknown>);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  };

  if (!config) return <div className="vision-settings-loading">Loading vision settings...</div>;

  return (
    <div className="vision-settings">
      <h3>Vision Settings</h3>

      <div className="settings-group">
        <label>Vision Provider</label>
        <select
          value={config.provider}
          onChange={(e) => setConfig({ ...config, provider: e.target.value })}
        >
          {providers.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      <div className="settings-group">
        <label>OCR Engine</label>
        <select
          value={config.ocr_engine}
          onChange={(e) => setConfig({ ...config, ocr_engine: e.target.value })}
        >
          <option value="tesseract">Tesseract</option>
          <option value="easyocr">EasyOCR</option>
          <option value="mock">Mock (Testing)</option>
        </select>
      </div>

      <div className="settings-group">
        <label>Capture Quality: {config.capture_quality}%</label>
        <input
          type="range"
          min="10"
          max="100"
          value={config.capture_quality}
          onChange={(e) => setConfig({ ...config, capture_quality: parseInt(e.target.value) })}
        />
      </div>

      <div className="settings-group">
        <label>Observation Mode</label>
        <select
          value={config.observation_mode}
          onChange={(e) => setConfig({ ...config, observation_mode: e.target.value })}
        >
          <option value="manual">Manual</option>
          <option value="live">Live</option>
        </select>
      </div>

      <div className="settings-group checkbox">
        <input
          type="checkbox"
          id="privacy_filters"
          checked={config.privacy_filters}
          onChange={(e) => setConfig({ ...config, privacy_filters: e.target.checked })}
        />
        <label htmlFor="privacy_filters">Enable privacy filters</label>
      </div>

      <div className="settings-group checkbox">
        <input
          type="checkbox"
          id="auto_redact"
          checked={config.auto_redact}
          onChange={(e) => setConfig({ ...config, auto_redact: e.target.checked })}
        />
        <label htmlFor="auto_redact">Auto-redact sensitive text</label>
      </div>

      {monitors.length > 0 && (
        <div className="settings-group">
          <label>Monitor</label>
          <select
            value={config.observation_mode === "live" ? "0" : "0"}
            onChange={() => {}}
          >
            {monitors.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name} ({m.width}×{m.height}){m.is_primary ? " (Primary)" : ""}
              </option>
            ))}
          </select>
        </div>
      )}

      {error && <div className="settings-error">{error}</div>}

      <button className="settings-save-btn" onClick={handleSave} disabled={saving}>
        {saving ? "Saving..." : saved ? "Saved ✓" : "Save Settings"}
      </button>
    </div>
  );
}
