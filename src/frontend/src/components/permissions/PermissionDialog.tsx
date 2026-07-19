import { useState, useEffect } from "react";

interface PermissionRequest {
  id: string;
  tool_id: string;
  level: number;
  description: string;
  created_at: string;
}

interface PermissionDialogProps {
  request: PermissionRequest;
  onGrant: (id: string) => void;
  onDeny: (id: string) => void;
}

const levelLabels: Record<number, string> = {
  0: "Safe",
  1: "Low Risk",
  2: "Medium Risk",
  3: "High Risk",
  4: "Critical",
};

export default function PermissionDialog({ request, onGrant, onDeny }: PermissionDialogProps) {
  return (
    <div className="permission-dialog-overlay">
      <div className="permission-dialog">
        <div className="permission-header">
          <div className="permission-icon">🔒</div>
          <h2>Permission Required</h2>
        </div>
        <div className="permission-body">
          <p className="permission-desc">{request.description}</p>
          <div className="permission-level">
            <span className="level-badge" data-level={request.level}>
              Level {request.level}
            </span>
            <span className="level-label">
              {request.level === 0 && "Safe"}
              {request.level === 1 && "Low Risk"}
              {request.level === 2 && "Medium Risk"}
              {request.level === 3 && "High Risk"}
              {request.level === 4 && "Critical"}
            </span>
          </div>
        </div>
        <div className="permission-actions">
          <button className="btn btn-secondary" onClick={() => onDeny(request.id)}>
            Deny
          </button>
          <button className="btn btn-primary" onClick={() => onGrant(request.id)}>
            Allow
          </button>
        </div>
      </div>
    </div>
  );
}
