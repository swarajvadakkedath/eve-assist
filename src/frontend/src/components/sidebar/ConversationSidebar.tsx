import { useState, useEffect } from "react";

interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
  is_active: boolean;
}

interface ConversationSidebarProps {
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
}

export default function ConversationSidebar({
  activeId, onSelect, onNew, onDelete, onRename,
}: ConversationSidebarProps) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [renamingId, setRenamingId] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState("");

  useEffect(() => {
    fetchConversations();
  }, []);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const res = await fetch("/api/v1/chat/conversations");
      const data = await res.json();
      setConversations(data.conversations || []);
    } catch (err) {
      console.error("Failed to fetch conversations", err);
    } finally {
      setLoading(false);
    }
  };

  const filtered = search
    ? conversations.filter((c) =>
        c.title.toLowerCase().includes(search.toLowerCase())
      )
    : conversations;

  const handleRenameStart = (conv: Conversation) => {
    setRenamingId(conv.id);
    setRenameValue(conv.title);
  };

  const handleRenameSubmit = async (id: string) => {
    if (renameValue.trim()) {
      try {
        await fetch(`/api/v1/chat/conversation/${id}?title=${encodeURIComponent(renameValue)}`, {
          method: "PUT",
        });
        onRename(id, renameValue);
        fetchConversations();
      } catch (err) {
        console.error("Rename failed", err);
      }
    }
    setRenamingId(null);
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h2>Conversations</h2>
        <button className="btn-new-chat" onClick={onNew} title="New conversation">
          +
        </button>
      </div>
      <div className="sidebar-search">
        <input
          type="text"
          placeholder="Search conversations..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <div className="sidebar-list">
        {loading && <div className="sidebar-loading">Loading...</div>}
        {!loading && filtered.length === 0 && (
          <div className="sidebar-empty">
            {search ? "No conversations found" : "No conversations yet"}
          </div>
        )}
        {filtered.map((conv) => (
          <div
            key={conv.id}
            className={`sidebar-item ${conv.id === activeId ? "active" : ""}`}
            onClick={() => onSelect(conv.id)}
          >
            {renamingId === conv.id ? (
              <input
                className="sidebar-rename-input"
                value={renameValue}
                onChange={(e) => setRenameValue(e.target.value)}
                onBlur={() => handleRenameSubmit(conv.id)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleRenameSubmit(conv.id);
                  if (e.key === "Escape") setRenamingId(null);
                }}
                autoFocus
                onClick={(e) => e.stopPropagation()}
              />
            ) : (
              <>
                <div className="sidebar-item-title" onDoubleClick={() => handleRenameStart(conv)}>
                  {conv.title}
                </div>
                <div className="sidebar-item-meta">
                  <span>{conv.message_count} messages</span>
                </div>
                <button
                  className="sidebar-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm("Delete this conversation?")) {
                      onDelete(conv.id);
                      fetchConversations();
                    }
                  }}
                  title="Delete"
                >
                  ×
                </button>
              </>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
