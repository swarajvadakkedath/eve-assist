import type { ExecutionSession } from "../execution/session/types";

export interface InspectorMetadataProps {
  session: ExecutionSession;
}

function InspectorMetadata({ session }: InspectorMetadataProps) {
  const { metadata, id, conversationId, requestId, startedAt, completedAt, durationMs, status } = session;

  const fields: [string, string | number | undefined][] = [
    ["Session ID", id],
    ["Conversation ID", conversationId],
    ["Request ID", requestId],
    ["Status", status],
    ["Started", startedAt],
    ["Completed", completedAt],
    ["Duration", durationMs !== undefined ? `${durationMs}ms` : undefined],
    ["Tools Executed", metadata.toolCount],
    ["Files Changed", metadata.fileCount],
    ["Files Created", metadata.filesCreated],
    ["Files Read", metadata.filesRead],
    ["Files Modified", metadata.filesModified],
    ["Files Deleted", metadata.filesDeleted],
    ["Tokens Used", metadata.tokensUsed],
    ["Retries", metadata.retryCount],
    ["Permission Requests", metadata.permissionRequests],
  ];

  return (
    <div className="pr-inspector-section" role="tabpanel" aria-label="Metadata">
      <h3 className="pr-inspector-section-title">Session Metadata</h3>
      <div className="pr-inspector-metadata-grid">
        {fields.filter(([, v]) => v !== undefined && v !== null).map(([label, value]) => (
          <div key={label} className="pr-inspector-metadata-item">
            <span className="pr-inspector-metadata-label">{label}</span>
            <span className="pr-inspector-metadata-value">{String(value)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default InspectorMetadata;
