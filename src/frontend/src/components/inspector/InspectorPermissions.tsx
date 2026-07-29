import type { ExecutionSession } from "../execution/session/types";

export interface InspectorPermissionsProps {
  session: ExecutionSession;
}

function InspectorPermissions({ session }: InspectorPermissionsProps) {
  const { metadata } = session;
  const hasPermissions = metadata.permissionRequests > 0;

  if (!hasPermissions) {
    return (
      <div className="pr-inspector-section" role="tabpanel" aria-label="Permissions">
        <p className="pr-inspector-empty">No permission requests in this session.</p>
      </div>
    );
  }

  return (
    <div className="pr-inspector-section" role="tabpanel" aria-label="Permissions">
      <h3 className="pr-inspector-section-title">Permission Requests</h3>
      <div className="pr-inspector-permissions-list" role="list" aria-label="Permission requests">
        <div className="pr-inspector-permission-item" role="listitem">
          <span className="pr-inspector-permission-icon" aria-hidden="true">{'\uD83D\uDEE1'}</span>
          <div className="pr-inspector-permission-info">
            <span className="pr-inspector-permission-count">{metadata.permissionRequests} request{metadata.permissionRequests !== 1 ? "s" : ""}</span>
            <span className="pr-inspector-permission-desc">
              {session.status === "permission" ? "Awaiting user decision" : "Resolved"}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

export default InspectorPermissions;
