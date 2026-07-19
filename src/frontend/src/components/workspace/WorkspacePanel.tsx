import { useState, useEffect } from "react";

interface WorkspaceData {
  active_window: string;
  project_count: number;
  application_count: number;
  repository_count: number;
  editor_count: number;
  terminal_count: number;
}

interface Project {
  name: string;
  framework: string;
  language: string;
  root_path: string;
}

interface RepoData {
  branch: string;
  dirty: boolean;
  ahead: number;
  behind: number;
  remote: string;
  last_commit_message: string;
  modified_count: number;
  staged_count: number;
}

interface EditorData {
  name: string;
  active_file: string;
  file_language: string;
  pid: number;
}

interface AppData {
  process_name: string;
  window_title: string;
  category: string;
}

interface TermData {
  cwd: string;
  shell: string;
  pid: number;
}

export default function WorkspacePanel() {
  const [workspace, setWorkspace] = useState<WorkspaceData | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [repos, setRepos] = useState<RepoData[]>([]);
  const [editors, setEditors] = useState<EditorData[]>([]);
  const [apps, setApps] = useState<AppData[]>([]);
  const [terminals, setTerminals] = useState<TermData[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(true);

  useEffect(() => {
    const fetchAll = async () => {
      try {
        const [w, p, g, e, a, t] = await Promise.all([
          fetch("/api/v1/workspace/current").then(r => r.json()),
          fetch("/api/v1/workspace/projects").then(r => r.json()),
          fetch("/api/v1/workspace/git").then(r => r.json()),
          fetch("/api/v1/workspace/editors").then(r => r.json()),
          fetch("/api/v1/workspace/applications").then(r => r.json()),
          fetch("/api/v1/workspace/terminals").then(r => r.json()),
        ]);
        setWorkspace(w);
        setProjects(p.projects || []);
        setRepos(g.repositories || []);
        setEditors(e.editors || []);
        setApps(a.applications || []);
        setTerminals(t.terminals || []);
      } catch {}
      setLoading(false);
    };
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="workspace-panel">
        <div className="workspace-loading">Loading workspace...</div>
      </div>
    );
  }

  return (
    <div className="workspace-panel">
      <div className="workspace-header" onClick={() => setExpanded(!expanded)} style={{ cursor: "pointer" }}>
        <span className="workspace-title">Workspace</span>
        <span className="workspace-active-window">
          {workspace?.active_window?.slice(0, 30) || ""}
        </span>
        <span>{expanded ? "▼" : "▶"}</span>
      </div>

      {expanded && (
        <div className="workspace-body">
          {projects.length > 0 && (
            <>
              <div className="workspace-section-title">Project</div>
              {projects.map((p, i) => (
                <div key={i} className="workspace-item">
                  <span className="workspace-item-label">{p.name}</span>
                  <span className="workspace-item-value">{p.framework} · {p.language}</span>
                </div>
              ))}
            </>
          )}

          {repos.length > 0 && (
            <>
              <div className="workspace-section-title">Git</div>
              {repos.map((r, i) => (
                <div key={i} className="workspace-item">
                  <span className="workspace-item-label">
                    {r.branch}{r.dirty ? <span className="workspace-dirty"> dirty</span> : ""}
                  </span>
                  <span className="workspace-item-value">
                    {r.modified_count > 0 ? `${r.modified_count} modified` : "clean"}
                    {r.ahead > 0 ? ` · ${r.ahead} ahead` : ""}
                    {r.behind > 0 ? ` · ${r.behind} behind` : ""}
                  </span>
                </div>
              ))}
            </>
          )}

          {editors.length > 0 && (
            <>
              <div className="workspace-section-title">Editor</div>
              {editors.map((e, i) => (
                <div key={i} className="workspace-item">
                  <span className="workspace-item-label">{e.name}</span>
                  <span className="workspace-item-value">{e.active_file || "no file open"}</span>
                </div>
              ))}
            </>
          )}

          {apps.length > 0 && (
            <>
              <div className="workspace-section-title">Applications</div>
              {apps.slice(0, 5).map((a, i) => (
                <div key={i} className="workspace-item">
                  <span className="workspace-item-label">{a.process_name}</span>
                  <span className="workspace-item-value">{a.window_title.slice(0, 30)}</span>
                </div>
              ))}
            </>
          )}

          {terminals.length > 0 && (
            <>
              <div className="workspace-section-title">Terminals</div>
              {terminals.map((t, i) => (
                <div key={i} className="workspace-item">
                  <span className="workspace-item-label">{t.shell}</span>
                  <span className="workspace-item-value">{t.cwd.slice(0, 40)}</span>
                </div>
              ))}
            </>
          )}

          {projects.length === 0 && repos.length === 0 && editors.length === 0 && apps.length === 0 && (
            <div className="workspace-empty">No workspace data available</div>
          )}
        </div>
      )}
    </div>
  );
}
