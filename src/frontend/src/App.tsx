import { useState, useEffect } from "react";
import ConversationView from "./components/conversation/ConversationView";
import WorkspaceRegistry from "./components/workspace/WorkspaceRegistry";
import type { WorkspaceDefinition } from "./components/workspace/WorkspaceRegistry";
import { useCommandPalette } from "./components/command/CommandPalette";
import SettingsPanel from "./components/desktop/SettingsPanel";
import PluginManagerPanel from "./components/plugins/PluginManagerPanel";
import ToolCenterPanel from "./components/tools/ToolCenterPanel";
import StatusIndicator from "./components/desktop/StatusIndicator";
import NotificationCenter from "./components/desktop/NotificationCenter";
import VoiceButton from "./components/voice/VoiceButton";
import VoiceIndicator from "./components/voice/VoiceIndicator";
import InterruptButton from "./components/voice/InterruptButton";
import TranscriptPanel from "./components/voice/TranscriptPanel";
import { voiceService } from "./services/voice";
import { api } from "./services/api";
import ScreenCaptureButton from "./components/vision/ScreenCaptureButton";
import ObservationPanel from "./components/vision/ObservationPanel";
import LivePreview from "./components/vision/LivePreview";
import ImageUpload from "./components/vision/ImageUpload";
import ActivityCenter from "./components/activity/ActivityCenter";

const workspaces: WorkspaceDefinition[] = [
  { id: "conversation", label: "Chat", icon: "\u{1F4AC}", component: ConversationView },
  { id: "activity", label: "Activity", icon: "\u{1F4CB}", component: ActivityCenter },
];

function App() {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [activeWorkspace, setActiveWorkspace] = useState("conversation");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [pluginsOpen, setPluginsOpen] = useState(false);
  const [toolsOpen, setToolsOpen] = useState(false);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [visionOpen, setVisionOpen] = useState(false);
  const [visionMode, setVisionMode] = useState<"observation" | "live" | "upload" | null>(null);

  const handleVoiceToggle = async () => {
    try {
      const s = voiceService.state;
      if (s.isListening) {
        await voiceService.stopListening();
      } else {
        await voiceService.connect();
        if (!s.sessionId) {
          await voiceService.startSession();
        }
        await voiceService.startListening();
      }
    } catch (e) {
      console.error("voice toggle error", e);
    }
  };

  const handleNavigate = (action: string, payload?: string) => {
    switch (action) {
      case "settings": setSettingsOpen(true); break;
      case "plugins": setPluginsOpen(true); break;
      case "vision": setVisionOpen(true); setVisionMode("observation"); break;
      case "theme": setTheme((t) => (t === "dark" ? "light" : "dark")); break;
      case "new_conversation": window.dispatchEvent(new CustomEvent("aios:new-conversation")); break;
      case "open_conversation":
        if (payload) window.dispatchEvent(new CustomEvent("aios:open-conversation", { detail: { id: payload } }));
        break;
      case "clear": window.dispatchEvent(new CustomEvent("aios:clear-chat")); break;
      case "help": window.dispatchEvent(new CustomEvent("aios:help")); break;
      case "export": window.dispatchEvent(new CustomEvent("aios:export")); break;
      case "search": window.dispatchEvent(new CustomEvent("aios:search")); break;
      case "tools": setToolsOpen(true); break;
      case "panel": window.dispatchEvent(new CustomEvent("aios:toggle-panel", { detail: { panel: payload } })); break;
      case "command": window.dispatchEvent(new CustomEvent("aios:command", { detail: { command: payload } })); break;
      case "url": window.open(payload, "_blank"); break;
      case "conversation": if (payload === "new") window.dispatchEvent(new CustomEvent("aios:new-conversation")); break;
      case "workspace":
        if (payload && workspaces.some((w) => w.id === payload)) setActiveWorkspace(payload);
        break;
    }
  };

  const { renderPalette, openPalette } = useCommandPalette(
    workspaces.map((w) => ({ id: w.id, label: w.label, icon: w.icon })),
    handleNavigate,
    (workspaceId) => setActiveWorkspace(workspaceId),
    activeWorkspace,
  );

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === ",") {
        e.preventDefault();
        setSettingsOpen((v) => !v);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "p") {
        e.preventDefault();
        setPluginsOpen((v) => !v);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "t") {
        e.preventDefault();
        setToolsOpen((v) => !v);
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "m") {
        e.preventDefault();
        handleVoiceToggle();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "i") {
        e.preventDefault();
        setVisionOpen((v) => !v);
        setVisionMode("observation");
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  useEffect(() => {
    voiceService.connect().catch(() => {});
    return () => { voiceService.disconnect(); };
  }, []);

  return (
    <div className={`app ${theme}`}>
      <div className="app-header">
        <StatusIndicator />
        <div className="app-header-center">
          <VoiceIndicator compact />
          <InterruptButton />
        </div>
        <div className="app-header-actions">
          <TranscriptPanel compact />
          <ScreenCaptureButton
            onCapture={() => { setVisionOpen(true); setVisionMode("observation"); }}
            onError={(e) => console.error(e)}
          />
          <VoiceButton />
          <NotificationCenter />
          <button className="btn-icon" onClick={() => setToolsOpen(true)} title="Tool Center (Ctrl+T)">
            🛠
          </button>
          <button className="btn-icon" onClick={() => setPluginsOpen(true)} title="Plugin Manager (Ctrl+P)">
            ■
          </button>
          <button className="btn-icon" onClick={() => openPalette()} title="Commands (Ctrl+K)">
            ⌘
          </button>
          <button className="btn-icon" onClick={() => setSettingsOpen(true)} title="Settings (Ctrl+,)">
            ⚙
          </button>
        </div>
      </div>
      <WorkspaceRegistry workspaces={workspaces} activeId={activeWorkspace} />
      {renderPalette}
      {settingsOpen && <SettingsPanel onClose={() => setSettingsOpen(false)} />}
      {toolsOpen && <ToolCenterPanel onClose={() => setToolsOpen(false)} />}
      {pluginsOpen && <PluginManagerPanel onClose={() => setPluginsOpen(false)} />}

      {visionOpen && visionMode === "observation" && (
        <div className="vision-panel-overlay" onClick={() => { setVisionOpen(false); setVisionMode(null); }}>
          <div onClick={(e) => e.stopPropagation()}>
            <ObservationPanel onClose={() => { setVisionOpen(false); setVisionMode(null); }} />
          </div>
        </div>
      )}
      {visionOpen && visionMode === "live" && (
        <div className="vision-panel-overlay" onClick={() => { setVisionOpen(false); setVisionMode(null); }}>
          <div onClick={(e) => e.stopPropagation()}>
            <LivePreview onClose={() => { setVisionOpen(false); setVisionMode(null); }} />
          </div>
        </div>
      )}
      {visionOpen && visionMode === "upload" && (
        <div className="vision-panel-overlay" onClick={() => { setVisionOpen(false); setVisionMode(null); }}>
          <div onClick={(e) => e.stopPropagation()}>
            <div className="vision-upload-wrapper">
              <ImageUpload
                onImageSelected={async (file) => {
                  try {
                    const data = await api.vision.analyzeUpload(file);
                    console.log("Upload analysis:", data);
                  } catch (e) {
                    console.error("Upload error", e);
                  }
                }}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
