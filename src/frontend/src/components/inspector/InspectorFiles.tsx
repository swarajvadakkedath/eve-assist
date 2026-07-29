import type { ExecutionSession } from "../execution/session/types";

export interface InspectorFilesProps {
  session: ExecutionSession;
}

interface FileGroup {
  label: string;
  count: number;
  icon: string;
  className: string;
}

function InspectorFiles({ session }: InspectorFilesProps) {
  const { metadata, steps } = session;
  const hasFiles = metadata.filesCreated > 0 || metadata.filesRead > 0
    || metadata.filesModified > 0 || metadata.filesDeleted > 0;

  const groups: FileGroup[] = [
    { label: "Created", count: metadata.filesCreated, icon: "+", className: "pr-inspector-file-created" },
    { label: "Read", count: metadata.filesRead, icon: "\u2192", className: "pr-inspector-file-read" },
    { label: "Modified", count: metadata.filesModified, icon: "~", className: "pr-inspector-file-modified" },
    { label: "Deleted", count: metadata.filesDeleted, icon: "-", className: "pr-inspector-file-deleted" },
  ];

  const hasAny = groups.some(g => g.count > 0);

  if (!hasAny) {
    return (
      <div className="pr-inspector-section" role="tabpanel" aria-label="Files">
        <p className="pr-inspector-empty">No file operations in this session.</p>
      </div>
    );
  }

  return (
    <div className="pr-inspector-section" role="tabpanel" aria-label="Files">
      <h3 className="pr-inspector-section-title">Files Affected</h3>
      <div className="pr-inspector-files-grid">
        {groups.filter(g => g.count > 0).map(g => (
          <div key={g.label} className={`pr-inspector-file-group ${g.className}`}>
            <span className="pr-inspector-file-icon" aria-hidden="true">{g.icon}</span>
            <div className="pr-inspector-file-info">
              <span className="pr-inspector-file-count">{g.count}</span>
              <span className="pr-inspector-file-label">{g.label}</span>
            </div>
          </div>
        ))}
      </div>

      {steps.length > 0 && (
        <div className="pr-inspector-files-step-list" role="list" aria-label="File operation steps">
          {steps.filter(s =>
            s.capability.includes("create") || s.capability.includes("write") ||
            s.capability.includes("read") || s.capability.includes("list") ||
            s.capability.includes("modify") || s.capability.includes("edit") ||
            s.capability.includes("delete") || s.capability.includes("remove")
          ).map(step => (
            <div key={step.id} className="pr-inspector-file-step" role="listitem">
              <span className={`pr-inspector-tool-status pr-inspector-status-${step.status}`} aria-hidden="true" />
              <span className="pr-inspector-file-step-name">{step.label}</span>
              <span className="pr-inspector-file-step-cap">{step.capability}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default InspectorFiles;
