import { useState, useEffect, useCallback } from "react";
import { fetchApi } from "../../services/api";
import AIProviderCard from "./AIProviderCard";
import ProviderConfigurationDialog from "./ProviderConfigurationDialog";
import AddProviderDialog from "./AddProviderDialog";
import SmartRoutingPanel from "./SmartRoutingPanel";
import type { ProviderInfo } from "./types";

interface ManageProvidersPageProps {
  onClose: () => void;
}

export default function ManageProvidersPage({ onClose }: ManageProvidersPageProps) {
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [firstRunTest, setFirstRunTest] = useState(false);
  const [showConfigForType, setShowConfigForType] = useState<{
    id: string;
    name: string;
    needs_endpoint: boolean;
    default_endpoint: string;
  } | null>(null);

  const fetchProviders = useCallback(async () => {
    try {
      const res = await fetchApi("/providers");
      const data = await res.json();
      setProviders(data.providers || []);
    } catch {} finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const handleAddProviderSelect = (type: { id: string; name: string; needs_endpoint: boolean; default_endpoint: string }) => {
    setShowAddDialog(false);
    setShowConfigForType(type);
  };

  const handleConfigSave = () => {
    setShowConfigForType(null);
    fetchProviders();
    setFirstRunTest(true);
  };

  const handleProviderUpdate = () => {
    fetchProviders();
  };

  const handleProviderRemove = (id: string) => {
    setProviders((prev) => prev.filter((p) => p.id !== id));
  };

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === "Escape" && !showAddDialog && !showConfigForType) {
        onClose();
      }
    },
    [onClose, showAddDialog, showConfigForType]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  const handleCloseOverlay = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget && !showAddDialog && !showConfigForType) {
      onClose();
    }
  };

  useEffect(() => {
    if (firstRunTest) {
      const timeout = setTimeout(async () => {
        try {
          await fetchApi("/providers/test-all", { method: "POST" });
          fetchProviders();
        } catch {}
      }, 500);
      return () => clearTimeout(timeout);
    }
  }, [firstRunTest, fetchProviders]);

  const hasProviders = providers.length > 0;

  return (
    <div className="settings-panel-overlay" onClick={handleCloseOverlay}>
      <div
        className="pr-providers-page"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="pr-providers-page-header">
          <div>
            <h1 className="pr-providers-page-title">AI Providers</h1>
            <p className="pr-providers-page-subtitle">
              Manage AI provider connections, API keys, and routing
            </p>
          </div>
          <div className="pr-providers-page-actions">
            <button className="btn-close" onClick={onClose}>&times;</button>
          </div>
        </div>

        <div className="pr-providers-page-body">
          {loading ? (
            <div className="pr-providers-loading">
              <div className="pr-spinner" />
              <p>Loading providers...</p>
            </div>
          ) : !hasProviders ? (
            <div className="pr-providers-empty">
              <div className="pr-providers-empty-icon">&#x1F916;</div>
              <h2>No AI Provider Configured</h2>
              <p>Connect your first AI provider to start using Eve OS.</p>
              <p className="pr-providers-empty-sub">
                You can add multiple providers and route different tasks to different models.
              </p>
              <button
                className="btn btn-primary"
                style={{ marginTop: 24, padding: "12px 32px", fontSize: 15 }}
                onClick={() => setShowAddDialog(true)}
              >
                + Add Your First Provider
              </button>
            </div>
          ) : (
            <div className="pr-providers-content">
              <div className="pr-providers-grid">
                {providers.map((p) => (
                  <AIProviderCard
                    key={p.id}
                    provider={p}
                    onUpdate={handleProviderUpdate}
                    onRemove={handleProviderRemove}
                  />
                ))}

                <button
                  className="pr-provider-card pr-add-card"
                  onClick={() => setShowAddDialog(true)}
                >
                  <div className="pr-add-card-icon">+</div>
                  <div className="pr-add-card-text">Add Provider</div>
                </button>
              </div>

              <SmartRoutingPanel
                providers={providers}
                onUpdate={handleProviderUpdate}
              />
            </div>
          )}
        </div>
      </div>

      {showAddDialog && (
        <AddProviderDialog
          onSelect={handleAddProviderSelect}
          onClose={() => setShowAddDialog(false)}
        />
      )}

      {showConfigForType && (
        <ProviderConfigurationDialog
          provider={{
            type: showConfigForType.id,
            name: showConfigForType.name,
            endpoint_url: showConfigForType.default_endpoint,
          }}
          providerType={showConfigForType}
          onSave={handleConfigSave}
          onClose={() => setShowConfigForType(null)}
        />
      )}
    </div>
  );
}
