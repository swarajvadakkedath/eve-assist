import type { PermissionRequest } from "./types";

export interface PermissionCardProps {
  permission: PermissionRequest;
  onAllowOnce: () => void;
  onAlwaysAllow: () => void;
  onDeny: () => void;
}

function PermissionCard({ permission, onAllowOnce, onAlwaysAllow, onDeny }: PermissionCardProps) {
  return (
    <div className="pr-exec-permission" role="alertdialog" aria-label="Permission required" aria-describedby="perm-desc">
      <div className="pr-exec-permission-icon" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2" />
          <path d="M7 11V7a5 5 0 0110 0v4" />
        </svg>
      </div>
      <div className="pr-exec-permission-body">
        <div className="pr-exec-permission-title">Permission Required</div>
        <div className="pr-exec-permission-desc" id="perm-desc">
          {permission.description || `${permission.capability} requires your approval.`}
        </div>
        <div className="pr-exec-permission-actions">
          <button className="pr-exec-permission-btn pr-exec-permission-allow-once" onClick={onAllowOnce}>
            Allow Once
          </button>
          <button className="pr-exec-permission-btn pr-exec-permission-always-allow" onClick={onAlwaysAllow}>
            Always Allow
          </button>
          <button className="pr-exec-permission-btn pr-exec-permission-deny" onClick={onDeny}>
            Deny
          </button>
        </div>
      </div>
    </div>
  );
}

export default PermissionCard;
