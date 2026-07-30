import { useState, useEffect } from "react";
import { fetchApi } from "../../services/api";

interface ProviderTypeInfo {
  id: string;
  name: string;
  needs_endpoint: boolean;
  default_endpoint: string;
  has_models_endpoint: boolean;
}

interface AddProviderDialogProps {
  onSelect: (type: ProviderTypeInfo) => void;
  onClose: () => void;
}

const PROVIDER_ICONS: Record<string, string> = {
  google: "\u2601",
  groq: "\u26A1",
  openrouter: "\u2194",
  openai: "\u25CB",
  anthropic: "\u2728",
  mistral: "\uD83C\uDF2C",
  cerebras: "\u2B50",
  github_models: "\uD83D\uDCBB",
  huggingface: "\uD83D\uDCD8",
  ollama: "\uD83E\uDD16",
  lm_studio: "\uD83C\uDFAD",
  openai_compatible: "\u2699",
  custom: "\uD83D\uDD27",
};

export default function AddProviderDialog({ onSelect, onClose }: AddProviderDialogProps) {
  const [types, setTypes] = useState<ProviderTypeInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");

  useEffect(() => {
    fetchApi("/providers/available-types")
      .then((r) => r.json())
      .then((data) => {
        setTypes(data.types || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  const filtered = search
    ? types.filter((t) => t.name.toLowerCase().includes(search.toLowerCase()))
    : types;

  const handleClose = (e: React.MouseEvent) => {
    if (e.target === e.currentTarget) onClose();
  };

  return (
    <div className="settings-panel-overlay" onClick={handleClose}>
      <div className="pr-add-provider-dialog" onClick={(e) => e.stopPropagation()}>
        <div className="pr-add-provider-header">
          <h2>Add Provider</h2>
          <button className="btn-close" onClick={onClose}>&times;</button>
        </div>

        <div className="pr-add-provider-search">
          <input
            type="text"
            placeholder="Search providers..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            autoFocus
          />
        </div>

        <div className="pr-add-provider-grid">
          {loading ? (
            <div className="pr-add-provider-loading">Loading...</div>
          ) : filtered.length === 0 ? (
            <div className="pr-add-provider-empty">No providers match your search</div>
          ) : (
            filtered.map((t) => (
              <button
                key={t.id}
                className="pr-add-provider-item"
                onClick={() => onSelect(t)}
              >
                <span className="pr-add-provider-icon">
                  {PROVIDER_ICONS[t.id] || "\u2699"}
                </span>
                <span className="pr-add-provider-name">{t.name}</span>
              </button>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
