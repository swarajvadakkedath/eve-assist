import { useState, useEffect, useRef } from "react";
import { fetchApi } from "../../services/api";

interface Command {
  id: string;
  name: string;
  description: string;
  shortcut?: string;
  category: string;
  action: () => void;
}

interface CommandPaletteProps {
  onClose: () => void;
  onNavigate: (action: string, payload?: string) => void;
}

export default function CommandPalette({ onClose, onNavigate }: CommandPaletteProps) {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [conversations, setConversations] = useState<any[]>([]);
  const [tools, setTools] = useState<any[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
    Promise.all([
      fetchApi("/chat/conversations").then((r) => r.json()).catch(() => ({ conversations: [] })),
      fetchApi("/tools").then((r) => r.json()).catch(() => ({ tools: [] })),
    ]).then(([convData, toolData]) => {
      setConversations(convData.conversations || []);
      setTools(toolData.tools || []);
    });
  }, []);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const commands: Command[] = [
    { id: "new-conversation", name: "New Conversation", description: "Start a new conversation", shortcut: "Ctrl+Alt+E", category: "general", action: () => onNavigate("new_conversation") },
    { id: "settings", name: "Open Settings", description: "Configure AIOS settings", shortcut: "Ctrl+,", category: "general", action: () => onNavigate("settings") },
    { id: "theme", name: "Toggle Theme", description: "Switch between light and dark mode", category: "general", action: () => onNavigate("theme") },
    { id: "clear", name: "Clear Chat", description: "Clear the current conversation", category: "chat", action: () => onNavigate("clear") },
    { id: "help", name: "Help", description: "Show available commands", shortcut: "Ctrl+H", category: "general", action: () => onNavigate("help") },
    { id: "export", name: "Export Conversation", description: "Export current conversation", category: "chat", action: () => onNavigate("export") },
    { id: "search", name: "Search Conversations", description: "Search across all conversations", category: "chat", action: () => onNavigate("search") },
  ];

  const filteredCommands = query
    ? commands.filter(
        (c) =>
          c.name.toLowerCase().includes(query.toLowerCase()) ||
          c.description.toLowerCase().includes(query.toLowerCase())
      )
    : commands;

  const filteredConversations = query
    ? conversations.filter(
        (c: any) => c.title?.toLowerCase().includes(query.toLowerCase())
      )
    : [];

  const filteredTools = query
    ? tools.filter(
        (t: any) =>
          t.name?.toLowerCase().includes(query.toLowerCase()) ||
          t.description?.toLowerCase().includes(query.toLowerCase())
      )
    : [];

  const allItems = [
    ...filteredCommands.map((c) => ({ type: "command" as const, ...c })),
    ...filteredConversations.map((c) => ({ type: "conversation" as const, ...c })),
    ...filteredTools.map((t) => ({ type: "tool" as const, ...t })),
  ];

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((i) => Math.min(i + 1, allItems.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === "Enter" && allItems[selectedIndex]) {
      handleSelect(allItems[selectedIndex]);
    } else if (e.key === "Escape") {
      onClose();
    }
  };

  const handleSelect = (item: any) => {
    if (item.action) item.action();
    onClose();
  };

  return (
    <div className="command-palette-overlay" onClick={onClose}>
      <div className="command-palette" onClick={(e) => e.stopPropagation()}>
        <input
          ref={inputRef}
          type="text"
          className="command-input"
          placeholder="Search commands, conversations, tools..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={handleKeyDown}
        />
        <div className="command-list">
          {filteredCommands.length > 0 && (
            <>
              <div className="command-category">Commands</div>
              {filteredCommands.map((cmd, i) => (
                <div
                  key={cmd.id}
                  className={`command-item ${i === selectedIndex ? "selected" : ""}`}
                  onClick={() => handleSelect(cmd)}
                >
                  <div className="command-info">
                    <span className="command-name">{cmd.name}</span>
                    <span className="command-desc">{cmd.description}</span>
                  </div>
                  {cmd.shortcut && <span className="command-shortcut">{cmd.shortcut}</span>}
                </div>
              ))}
            </>
          )}
          {filteredConversations.length > 0 && (
            <>
              <div className="command-category">Conversations</div>
              {filteredConversations.map((c: any, i: number) => (
                <div
                  key={c.id}
                  className={`command-item ${i + filteredCommands.length === selectedIndex ? "selected" : ""}`}
                  onClick={() => onNavigate("open_conversation", c.id)}
                >
                  <div className="command-info">
                    <span className="command-name">{c.title || "Untitled"}</span>
                    <span className="command-desc">{new Date(c.updated_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))}
            </>
          )}
          {filteredTools.length > 0 && (
            <>
              <div className="command-category">Tools</div>
              {filteredTools.map((t: any, i: number) => (
                <div
                  key={t.id}
                  className={`command-item ${i + filteredCommands.length + filteredConversations.length === selectedIndex ? "selected" : ""}`}
                  onClick={() => handleSelect(t)}
                >
                  <div className="command-info">
                    <span className="command-name">{t.name}</span>
                    <span className="command-desc">{t.description}</span>
                  </div>
                </div>
              ))}
            </>
          )}
          {allItems.length === 0 && (
            <div className="command-empty">No results found</div>
          )}
        </div>
      </div>
    </div>
  );
}
