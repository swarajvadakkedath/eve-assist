import type { ExecutionSession, ExecutionStep, SessionMetadata, SessionResult, ExecutionSessionEvent } from "./types";
import { isSessionTerminal } from "./types";

function createDefaultMetadata(): SessionMetadata {
  return {
    toolCount: 0,
    fileCount: 0,
    filesCreated: 0,
    filesRead: 0,
    filesModified: 0,
    filesDeleted: 0,
    tokensUsed: 0,
    retryCount: 0,
    permissionRequests: 0,
  };
}

function extractFilesFromSteps(steps: ExecutionStep[]): { created: number; read: number; modified: number; deleted: number; total: number } {
  let created = 0, read = 0, modified = 0, deleted = 0;
  for (const step of steps) {
    const cap = step.capability;
    if (cap.includes("create") || cap.includes("write")) created++;
    else if (cap.includes("read") || cap.includes("list") || cap.includes("search")) read++;
    else if (cap.includes("modify") || cap.includes("edit") || cap.includes("update")) modified++;
    else if (cap.includes("delete") || cap.includes("remove")) deleted++;
  }
  return { created, read, modified, deleted, total: steps.length };
}

function computeSessionResult(session: ExecutionSession): SessionResult | undefined {
  if (!isSessionTerminal(session.status)) return undefined;
  const completedCount = session.steps.filter(s => s.status === "completed").length;
  const failedCount = session.steps.filter(s => s.status === "failed").length;
  const success = failedCount === 0 && completedCount > 0;
  return {
    success,
    summary: generateSummary(session),
    durationMs: session.durationMs || 0,
    toolCount: session.steps.length,
    completedCount,
    failedCount,
    toolsExecuted: session.steps.map(s => s.capability),
    capabilitiesUsed: [...new Set(session.steps.map(s => s.capability.split(".")[0]))],
    warnings: [],
    errors: failedCount > 0 ? session.steps.filter(s => s.error).map(s => s.error!) : [],
  };
}

export function generateSummary(session: ExecutionSession): string {
  const files = extractFilesFromSteps(session.steps);
  const parts: string[] = [];
  if (files.created > 0) parts.push(`Created ${files.created} file${files.created !== 1 ? "s" : ""}`);
  if (files.read > 0) parts.push(`Read ${files.read} file${files.read !== 1 ? "s" : ""}`);
  if (files.modified > 0) parts.push(`Modified ${files.modified} file${files.modified !== 1 ? "s" : ""}`);
  if (files.deleted > 0) parts.push(`Deleted ${files.deleted} file${files.deleted !== 1 ? "s" : ""}`);
  if (session.steps.length > 0 && parts.length === 0) {
    parts.push(`Executed ${session.steps.length} tool${session.steps.length !== 1 ? "s" : ""}`);
  }
  if (session.durationMs !== undefined) {
    const seconds = (session.durationMs / 1000).toFixed(1);
    parts.push(`Completed in ${seconds}s`);
  }
  return parts.length > 0 ? parts.join(" · ") : "No actions recorded";
}

export class ExecutionSessionStore {
  private sessions: Map<string, ExecutionSession> = new Map();
  private listeners: Set<() => void> = new Set();

  subscribe(listener: () => void): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  private notify(): void {
    this.listeners.forEach(fn => fn());
  }

  createSession(conversationId: string, requestId: string, title: string): ExecutionSession {
    const id = `session-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const session: ExecutionSession = {
      id,
      conversationId,
      requestId,
      title,
      status: "planning",
      startedAt: new Date().toISOString(),
      steps: [],
      logs: [],
      metadata: createDefaultMetadata(),
      collapsed: false,
    };
    this.sessions.set(id, session);
    this.notify();
    return session;
  }

  getSession(id: string): ExecutionSession | undefined {
    return this.sessions.get(id);
  }

  getAllSessions(conversationId: string): ExecutionSession[] {
    const result: ExecutionSession[] = [];
    for (const session of this.sessions.values()) {
      if (session.conversationId === conversationId) {
        result.push(session);
      }
    }
    result.sort((a, b) => new Date(a.startedAt).getTime() - new Date(b.startedAt).getTime());
    return result;
  }

  getActiveSession(conversationId: string): ExecutionSession | undefined {
    for (const session of this.sessions.values()) {
      if (session.conversationId === conversationId && !isSessionTerminal(session.status)) {
        return session;
      }
    }
    return undefined;
  }

  updateSession(id: string, updates: Partial<ExecutionSession>): void {
    const existing = this.sessions.get(id);
    if (!existing) return;
    this.sessions.set(id, { ...existing, ...updates });
    this.notify();
  }

  deleteSession(id: string): void {
    this.sessions.delete(id);
    this.notify();
  }

  getAllGlobalSessions(): ExecutionSession[] {
    const result: ExecutionSession[] = [];
    for (const session of this.sessions.values()) {
      result.push(session);
    }
    result.sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime());
    return result;
  }

  clearConversation(conversationId: string): void {
    for (const [id, session] of this.sessions) {
      if (session.conversationId === conversationId) {
        this.sessions.delete(id);
      }
    }
    this.notify();
  }

  toggleCollapse(id: string): void {
    const session = this.sessions.get(id);
    if (!session) return;
    session.collapsed = !session.collapsed;
    this.notify();
  }

  applyEvent(event: ExecutionSessionEvent): void {
    switch (event.type) {
      case "ExecutionStarted": {
        const session: ExecutionSession = {
          id: event.sessionId,
          conversationId: event.conversationId,
          requestId: event.requestId,
          title: event.request.slice(0, 80),
          status: "planning",
          startedAt: new Date().toISOString(),
          steps: [],
          logs: [],
          metadata: createDefaultMetadata(),
          collapsed: false,
        };
        this.sessions.set(session.id, session);
        this.notify();
        break;
      }

      case "PlanningStarted": {
        const session = this.sessions.get(event.sessionId);
        if (session) this.updateSession(session.id, { status: "planning" });
        break;
      }

      case "PlanningCompleted": {
        const session = this.sessions.get(event.sessionId);
        if (session) this.updateSession(session.id, { status: "running" });
        break;
      }

      case "StepScheduled": {
        const session = this.sessions.get(event.sessionId);
        if (!session) return;
        const step: ExecutionStep = {
          id: `step-${session.steps.length}`,
          capability: event.capability,
          label: event.toolName,
          status: "pending",
          startedAt: new Date().toISOString(),
        };
        const steps = [...session.steps, step];
        const metadata = { ...session.metadata, toolCount: steps.length };
        this.updateSession(session.id, { steps, metadata, status: "running" });
        break;
      }

      case "StepStarted": {
        const session = this.sessions.get(event.sessionId);
        if (!session) return;
        const steps = session.steps.map(s =>
          s.label === event.toolName ? { ...s, status: "running" as const } : s
        );
        this.updateSession(session.id, { steps, status: "running" });
        break;
      }

      case "StepUpdated": {
        const session = this.sessions.get(event.sessionId);
        if (!session) return;
        const steps = session.steps.map(s =>
          s.label === event.toolName ? { ...s, status: "running" as const } : s
        );
        this.updateSession(session.id, { steps });
        break;
      }

      case "StepCompleted": {
        const session = this.sessions.get(event.sessionId);
        if (!session) return;
        const now = new Date().toISOString();
        const steps = session.steps.map(s => {
          if (s.label !== event.toolName) return s;
          const started = s.startedAt ? new Date(s.startedAt).getTime() : Date.now();
          return {
            ...s,
            status: event.success ? "completed" as const : "failed" as const,
            completedAt: now,
            durationMs: Date.now() - started,
            error: event.success ? undefined : `Step failed`,
          };
        });
        const files = extractFilesFromSteps(steps);
        const metadata: SessionMetadata = {
          ...session.metadata,
          toolCount: steps.length,
          filesCreated: files.created,
          filesRead: files.read,
          filesModified: files.modified,
          filesDeleted: files.deleted,
          fileCount: files.total,
        };
        const allDone = steps.every(s => s.status === "completed" || s.status === "failed" || s.status === "skipped");
        this.updateSession(session.id, { steps, metadata, status: allDone ? "completed" : "running" });
        break;
      }

      case "PermissionRequested": {
        const session = this.sessions.get(event.sessionId);
        if (session) {
          this.updateSession(session.id, {
            status: "permission",
            metadata: { ...session.metadata, permissionRequests: session.metadata.permissionRequests + 1 },
          });
        }
        break;
      }

      case "PermissionGranted": {
        const session = this.sessions.get(event.sessionId);
        if (session) this.updateSession(session.id, { status: "running" });
        break;
      }

      case "ExecutionCompleted": {
        const session = this.sessions.get(event.sessionId);
        if (!session) return;
        const completedAt = new Date().toISOString();
        const durationMs = event.durationMs || Date.now() - new Date(session.startedAt).getTime();
        const result = computeSessionResult({ ...session, status: "completed", completedAt, durationMs });
        this.updateSession(session.id, {
          status: "completed",
          completedAt,
          durationMs,
          result,
          collapsed: true,
        });
        break;
      }

      case "ExecutionFailed": {
        const session = this.sessions.get(event.sessionId);
        if (!session) return;
        const completedAt = new Date().toISOString();
        const durationMs = Date.now() - new Date(session.startedAt).getTime();
        const result = computeSessionResult({ ...session, status: "failed", completedAt, durationMs });
        this.updateSession(session.id, {
          status: "failed",
          completedAt,
          durationMs,
          error: event.error,
          result,
          collapsed: false,
        });
        break;
      }

      case "ExecutionCancelled": {
        const session = this.sessions.get(event.sessionId);
        if (!session) return;
        const completedAt = new Date().toISOString();
        const durationMs = Date.now() - new Date(session.startedAt).getTime();
        this.updateSession(session.id, {
          status: "cancelled",
          completedAt,
          durationMs,
          collapsed: false,
        });
        break;
      }
    }
  }
}

let globalInstance: ExecutionSessionStore | null = null;

export function getSessionStore(): ExecutionSessionStore {
  if (!globalInstance) {
    globalInstance = new ExecutionSessionStore();
  }
  return globalInstance;
}
