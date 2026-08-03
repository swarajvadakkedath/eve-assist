import { useState, useEffect, useRef } from "react";
import { fetchApi } from "../../services/api";

interface Execution {
  id: string;
  status: string;
  objective: string;
  priority: number;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
}

interface TaskSummary {
  id: string;
  capability: string;
  tool: string;
  status: string;
  retries: number;
  error: string | null;
  duration_ms: number;
  is_optional: boolean;
}

interface ExecutionProgress {
  percentage: number;
  current_capability: string;
  completed_tasks: number;
  total_tasks: number;
  remaining_tasks: number;
  status: string;
}

const STATUS_COLORS: Record<string, string> = {
  pending: "#9ca3af",
  planning: "#fbbf24",
  waiting_for_permission: "#f97316",
  ready: "#6366f1",
  running: "#22c55e",
  waiting: "#9ca3af",
  retrying: "#f97316",
  paused: "#fbbf24",
  cancelled: "#ef4444",
  completed: "#22c55e",
  failed: "#ef4444",
};

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  planning: "Planning",
  waiting_for_permission: "Waiting for Permission",
  ready: "Ready",
  running: "Running",
  waiting: "Waiting",
  retrying: "Retrying",
  paused: "Paused",
  cancelled: "Cancelled",
  completed: "Completed",
  failed: "Failed",
};

export default function ExecutionPanel({ executionId }: { executionId: string | null }) {
  const [execution, setExecution] = useState<Execution | null>(null);
  const [tasks, setTasks] = useState<TaskSummary[]>([]);
  const [progress, setProgress] = useState<ExecutionProgress | null>(null);
  const [expanded, setExpanded] = useState(true);
  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (!executionId) {
      setExecution(null);
      setTasks([]);
      setProgress(null);
      return;
    }

    const fetchData = async () => {
      try {
        const [execRes, progressRes] = await Promise.all([
          fetchApi(`/execution/${executionId}`).then((r) => r.json()),
          fetchApi(`/execution/${executionId}/progress`).then((r) => r.json()),
        ]);
        setExecution(execRes.execution);
        setTasks(execRes.tasks || []);
        setProgress(progressRes);
      } catch {}
    };

    fetchData();
    intervalRef.current = window.setInterval(fetchData, 1000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [executionId]);

  const handleAction = async (action: string) => {
    if (!executionId) return;
    try {
      await fetchApi(`/execution/${executionId}/${action}`, { method: "POST" });
    } catch {}
  };

  if (!executionId || !execution) return null;

  const isRunning = execution.status === "running" || execution.status === "planning";
  const progressPct = progress?.percentage || 0;

  return (
    <div className="execution-panel">
      <div className="execution-header" onClick={() => setExpanded(!expanded)}>
        <div className="execution-title">
          <span className="execution-status-dot" style={{ backgroundColor: STATUS_COLORS[execution.status] || "#9ca3af" }} />
          <span className="execution-objective">{execution.objective}</span>
        </div>
        <span className="execution-expand">{expanded ? "▼" : "▶"}</span>
      </div>

      {expanded && (
        <div className="execution-body">
          <div className="execution-status-bar">
            <div className="execution-status-label">
              {STATUS_LABELS[execution.status] || execution.status}
            </div>
            <div className="execution-progress-bar">
              <div
                className="execution-progress-fill"
                style={{ width: `${Math.round(progressPct)}%` }}
              />
            </div>
            <div className="execution-progress-text">
              {progress?.completed_tasks || 0} / {progress?.total_tasks || 0} tasks
              {progress?.current_capability && (
                <span className="execution-current-task">
                  &nbsp;· {progress.current_capability}
                </span>
              )}
            </div>
          </div>

          <div className="execution-actions">
            {isRunning && (
              <>
                <button className="btn btn-sm btn-warning" onClick={() => handleAction("pause")}>
                  ⏸ Pause
                </button>
                <button className="btn btn-sm btn-danger" onClick={() => handleAction("cancel")}>
                  ⏹ Cancel
                </button>
              </>
            )}
            {execution.status === "paused" && (
              <button className="btn btn-sm btn-primary" onClick={() => handleAction("resume")}>
                ▶ Resume
              </button>
            )}
          </div>

          {execution.status === "waiting_for_permission" && (
            <div className="execution-permission-request">
              ⚠ Waiting for permission to continue...
            </div>
          )}

          {tasks.length > 0 && (
            <div className="execution-tasks">
              <div className="execution-tasks-title">Tasks</div>
              {tasks.map((task) => (
                <div key={task.id} className={`execution-task execution-task-${task.status}`}>
                  <div className="execution-task-info">
                    <span className="execution-task-status">
                      {task.status === "success" ? "✅" : task.status === "failed" ? "❌" : task.status === "running" ? "🔄" : task.status === "pending" ? "⏳" : "⬜"}
                    </span>
                    <span className="execution-task-name">
                      {task.capability || task.tool}
                    </span>
                    {task.is_optional && <span className="execution-task-badge">optional</span>}
                  </div>
                  <div className="execution-task-meta">
                    {task.duration_ms > 0 && (
                      <span className="execution-task-duration">
                        {(task.duration_ms / 1000).toFixed(1)}s
                      </span>
                    )}
                    {task.retries > 0 && (
                      <span className="execution-task-retries">
                        retry {task.retries}
                      </span>
                    )}
                  </div>
                  {task.error && (
                    <div className="execution-task-error">{task.error}</div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
