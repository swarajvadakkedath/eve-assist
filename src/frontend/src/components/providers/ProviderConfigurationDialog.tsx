import { useState, useEffect, useRef } from "react";
import { fetchApi } from "../../services/api";
import ConnectionTester from "./ConnectionTester";

interface ProviderData {
  id?: string;
  type: string;
  name: string;
  endpoint_url?: string;
  organization?: string;
  temperature?: number;
  max_tokens?: number;
  streaming_enabled?: boolean;
  api_key?: string;
  has_api_key?: boolean;
}

interface ProviderConfigurationDialogProps {
  provider: ProviderData;
  providerType?: { id: string; name: string; needs_endpoint: boolean; default_endpoint: string };
  onSave: (data: ProviderData) => void;
  onClose: () => void;
}

export default function ProviderConfigurationDialog({
  provider,
  providerType,
  onSave,
  onClose,
}: ProviderConfigurationDialogProps) {
  const isNew = !provider.id;
  const [name, setName] = useState(provider.name || "");
  const [endpointUrl, setEndpointUrl] = useState(provider.endpoint_url || "");
  const [apiKey, setApiKey] = useState("");
  const [organization, setOrganization] = useState(provider.organization || "");
  const [temperature, setTemperature] = useState(
    provider.temperature != null ? String(provider.temperature) : "0.7"
  );
  const [maxTokens, setMaxTokens] = useState(
    provider.max_tokens != null ? String(provider.max_tokens) : "4096"
  );
  const [streamingEnabled, setStreamingEnabled] = useState(
    provider.streaming_enabled ?? true
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [providerId, setProviderId] = useState<string | null>(provider.id || null);
  const nameRef = useRef<HTMLInputElement>(null);

  const needsEndpoint = providerType?.needs_endpoint ||
    provider.type === "openai_compatible" ||
    provider.type === "custom" ||
    provider.type === "ollama" ||
    provider.type === "lm_studio";

  const canHaveOrganization = provider.type === "openai";

  useEffect(() => {
    if (isNew && nameRef.current) {
      nameRef.current.focus();
    }
  }, [isNew]);

  useEffect(() => {
    if (isNew && providerType) {
      setName(providerType.name);
      if (providerType.default_endpoint) {
        setEndpointUrl(providerType.default_endpoint);
      }
    }
  }, [isNew, providerType]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      const body: any = {
        provider_type: provider.type,
        name: name.trim() || provider.type,
        endpoint_url: endpointUrl.trim() || undefined,
        api_key: apiKey || undefined,
        organization: organization.trim() || undefined,
        temperature: temperature ? parseFloat(temperature) : undefined,
        max_tokens: maxTokens ? parseInt(maxTokens, 10) : undefined,
        streaming_enabled: streamingEnabled,
      };

      if (!isNew && provider.id) {
        const res = await fetchApi(`/providers/${provider.id}`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error((await res.json()).detail || "Save failed");
        const result = await res.json();
        setProviderId(result.id);
        onSave(result);
      } else {
        const res = await fetchApi("/providers", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        });
        if (!res.ok) throw new Error((await res.json()).detail || "Add failed");
        const result = await res.json();
        setProviderId(result.id);
        onSave(result);
      }
    } catch (e: any) {
      setError(e.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  const handleClose = () => {
    if (!saving) onClose();
  };

  return (
    <div className="settings-panel-overlay" onClick={handleClose}>
      <div className="settings-panel settings-panel-wide" onClick={(e) => e.stopPropagation()}
        style={{ maxHeight: "85vh" }}>
        <div className="settings-header">
          <h2>{isNew ? "Configure Provider" : "Edit Provider"}</h2>
          <button className="btn-close" onClick={handleClose}>&times;</button>
        </div>

        <div className="settings-body" style={{ overflowY: "auto", flex: 1 }}>
          {error && <div className="pr-form-error">{error}</div>}

          <div className="setting-group">
            <label>Provider Name</label>
            <input
              ref={nameRef}
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. My Google AI"
            />
          </div>

          {needsEndpoint && (
            <div className="setting-group">
              <label>Endpoint URL</label>
              <input
                type="text"
                value={endpointUrl}
                onChange={(e) => setEndpointUrl(e.target.value)}
                placeholder={
                  provider.type === "ollama" ? "http://localhost:11434" :
                  provider.type === "lm_studio" ? "http://localhost:1234/v1" :
                  "https://api.example.com/v1"
                }
              />
            </div>
          )}

          <div className="setting-group">
            <label>API Key</label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder={
                provider.has_api_key
                  ? "Enter new key to replace existing"
                  : "sk-..."
              }
            />
            {provider.has_api_key && (
              <div className="pr-hint">Key stored securely. Leave blank to keep existing.</div>
            )}
          </div>

          {canHaveOrganization && (
            <div className="setting-group">
              <label>Organization (optional)</label>
              <input
                type="text"
                value={organization}
                onChange={(e) => setOrganization(e.target.value)}
                placeholder="org-..."
              />
            </div>
          )}

          <div className="pr-form-row">
            <div className="setting-group" style={{ flex: 1 }}>
              <label>Temperature</label>
              <input
                type="number"
                min="0"
                max="2"
                step="0.1"
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
              />
            </div>
            <div className="setting-group" style={{ flex: 1 }}>
              <label>Max Tokens</label>
              <input
                type="number"
                min="1"
                max="1000000"
                step="1"
                value={maxTokens}
                onChange={(e) => setMaxTokens(e.target.value)}
              />
            </div>
          </div>

          <div className="setting-group">
            <label className="setting-toggle">
              <input
                type="checkbox"
                checked={streamingEnabled}
                onChange={(e) => setStreamingEnabled(e.target.checked)}
              />
              Enable Streaming
            </label>
          </div>

          {providerId && (
            <div className="pr-test-section">
              <label style={{ fontSize: 13, fontWeight: 500, color: "var(--text-secondary)", marginBottom: 8, display: "block" }}>
                Connection Test
              </label>
              <ConnectionTester providerId={providerId} />
            </div>
          )}
        </div>

        <div className="settings-footer">
          <button className="btn btn-secondary" onClick={handleClose} disabled={saving}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : isNew ? "Add Provider" : "Save Changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
