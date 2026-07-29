export interface Action {
  id: string;
  label: string;
  icon?: React.ReactNode;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
  onClick: () => void;
}

export interface ExecutionActionsProps {
  actions: Action[];
}

function ExecutionActions({ actions }: ExecutionActionsProps) {
  if (actions.length === 0) return null;

  return (
    <div className="pr-exec-actions">
      {actions.map((action) => {
        const cls = `pr-exec-action-btn ${action.variant === "danger" ? "pr-exec-action-danger" : action.variant === "primary" ? "pr-exec-action-primary" : "pr-exec-action-secondary"}`;
        return (
          <button
            key={action.id}
            className={cls}
            onClick={action.onClick}
            disabled={action.disabled}
            aria-label={action.label}
          >
            {action.icon && <span className="pr-exec-action-icon" aria-hidden="true">{action.icon}</span>}
            <span>{action.label}</span>
          </button>
        );
      })}
    </div>
  );
}

export default ExecutionActions;
