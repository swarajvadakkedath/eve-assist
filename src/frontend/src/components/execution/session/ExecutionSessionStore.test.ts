import { describe, it, expect, beforeEach } from "vitest";
import { ExecutionSessionStore, generateSummary } from "./ExecutionSessionStore";
import type { ExecutionSessionEvent } from "./types";

describe("ExecutionSessionStore", () => {
  let store: ExecutionSessionStore;

  beforeEach(() => {
    store = new ExecutionSessionStore();
  });

  it("creates a session", () => {
    const session = store.createSession("c1", "req-1", "Read my files");
    expect(session.id).toBeTruthy();
    expect(session.conversationId).toBe("c1");
    expect(session.requestId).toBe("req-1");
    expect(session.title).toBe("Read my files");
    expect(session.status).toBe("planning");
  });

  it("gets a session by id", () => {
    const created = store.createSession("c1", "req-1", "Test");
    const fetched = store.getSession(created.id);
    expect(fetched?.id).toBe(created.id);
  });

  it("returns undefined for unknown session", () => {
    expect(store.getSession("nonexistent")).toBeUndefined();
  });

  it("lists all sessions for a conversation ordered by creation", () => {
    const s1 = store.createSession("c1", "req-1", "First");
    const s2 = store.createSession("c1", "req-2", "Second");
    const s3 = store.createSession("c2", "req-3", "Other");
    const c1Sessions = store.getAllSessions("c1");
    expect(c1Sessions).toHaveLength(2);
    expect(c1Sessions[0].id).toBe(s1.id);
    expect(c1Sessions[1].id).toBe(s2.id);
    expect(store.getAllSessions("c2")).toHaveLength(1);
  });

  it("gets active session (non-terminal) for a conversation", () => {
    store.createSession("c1", "req-1", "Active");
    const active = store.getActiveSession("c1");
    expect(active).toBeDefined();
    expect(active!.status).toBe("planning");
  });

  it("returns undefined when no active session", () => {
    expect(store.getActiveSession("c1")).toBeUndefined();
  });

  it("updates session fields", () => {
    const session = store.createSession("c1", "req-1", "Test");
    store.updateSession(session.id, { status: "running", title: "Updated" });
    const updated = store.getSession(session.id);
    expect(updated?.status).toBe("running");
    expect(updated?.title).toBe("Updated");
  });

  it("deletes a session", () => {
    const session = store.createSession("c1", "req-1", "Test");
    store.deleteSession(session.id);
    expect(store.getSession(session.id)).toBeUndefined();
  });

  it("clears all sessions for a conversation", () => {
    store.createSession("c1", "req-1", "A");
    store.createSession("c1", "req-2", "B");
    store.createSession("c2", "req-3", "C");
    store.clearConversation("c1");
    expect(store.getAllSessions("c1")).toHaveLength(0);
    expect(store.getAllSessions("c2")).toHaveLength(1);
  });

  it("toggles session collapse", () => {
    const session = store.createSession("c1", "req-1", "Test");
    expect(session.collapsed).toBe(false);
    store.toggleCollapse(session.id);
    expect(store.getSession(session.id)?.collapsed).toBe(true);
    store.toggleCollapse(session.id);
    expect(store.getSession(session.id)?.collapsed).toBe(false);
  });

  it("notifies subscribers on state change", () => {
    let notified = false;
    store.subscribe(() => { notified = true; });
    store.createSession("c1", "req-1", "Test");
    expect(notified).toBe(true);
  });

  it("allows unsubscribe", () => {
    let count = 0;
    const unsub = store.subscribe(() => { count++; });
    unsub();
    store.createSession("c1", "req-1", "Test");
    expect(count).toBe(0);
  });
});

describe("ExecutionSessionStore - applyEvent", () => {
  let store: ExecutionSessionStore;
  let sessionId: string;

  function apply(event: ExecutionSessionEvent) {
    store.applyEvent(event);
  }

  beforeEach(() => {
    store = new ExecutionSessionStore();
    apply({ type: "ExecutionStarted", sessionId: "s1", request: "Read my files", conversationId: "c1", requestId: "req-1" });
    sessionId = "s1";
  });

  it("creates session on ExecutionStarted", () => {
    const session = store.getSession(sessionId);
    expect(session).toBeDefined();
    expect(session?.title).toBe("Read my files");
    expect(session?.status).toBe("planning");
  });

  it("transitions to running on PlanningCompleted", () => {
    apply({ type: "PlanningCompleted", sessionId, steps: 3 });
    expect(store.getSession(sessionId)?.status).toBe("running");
  });

  it("adds step on StepScheduled", () => {
    apply({ type: "StepScheduled", sessionId, toolName: "file.read", capability: "file.read" });
    const session = store.getSession(sessionId);
    expect(session?.steps).toHaveLength(1);
    expect(session?.steps[0].label).toBe("file.read");
    expect(session?.steps[0].status).toBe("pending");
    expect(session?.metadata.toolCount).toBe(1);
  });

  it("marks step running on StepStarted", () => {
    apply({ type: "StepScheduled", sessionId, toolName: "file.read", capability: "file.read" });
    apply({ type: "StepStarted", sessionId, toolName: "file.read" });
    expect(store.getSession(sessionId)?.steps[0].status).toBe("running");
  });

  it("marks step completed on StepCompleted", () => {
    apply({ type: "StepScheduled", sessionId, toolName: "file.read", capability: "file.read" });
    apply({ type: "StepStarted", sessionId, toolName: "file.read" });
    apply({ type: "StepCompleted", sessionId, toolName: "file.read", success: true, duration: 100 });
    const session = store.getSession(sessionId);
    expect(session?.steps[0].status).toBe("completed");
  });

  it("marks step failed on StepCompleted with success=false", () => {
    apply({ type: "StepScheduled", sessionId, toolName: "file.read", capability: "file.read" });
    apply({ type: "StepCompleted", sessionId, toolName: "file.read", success: false, duration: 100 });
    expect(store.getSession(sessionId)?.steps[0].status).toBe("failed");
  });

  it("sets permission status on PermissionRequested", () => {
    apply({ type: "PermissionRequested", sessionId, capability: "file.write", level: 2 });
    expect(store.getSession(sessionId)?.status).toBe("permission");
  });

  it("returns to running on PermissionGranted", () => {
    apply({ type: "PermissionRequested", sessionId, capability: "file.write", level: 2 });
    apply({ type: "PermissionGranted", sessionId });
    expect(store.getSession(sessionId)?.status).toBe("running");
  });

  it("marks completed on ExecutionCompleted", () => {
    apply({ type: "StepScheduled", sessionId, toolName: "file.read", capability: "file.read" });
    apply({ type: "StepCompleted", sessionId, toolName: "file.read", success: true, duration: 100 });
    apply({ type: "ExecutionCompleted", sessionId, success: true, summary: "Done", durationMs: 1000 });
    const session = store.getSession(sessionId);
    expect(session?.status).toBe("completed");
    expect(session?.completedAt).toBeDefined();
    expect(session?.collapsed).toBe(true);
    expect(session?.result).toBeDefined();
    expect(session?.result?.success).toBe(true);
  });

  it("marks failed on ExecutionFailed", () => {
    apply({ type: "ExecutionFailed", sessionId, error: "Something broke" });
    const session = store.getSession(sessionId);
    expect(session?.status).toBe("failed");
    expect(session?.error).toBe("Something broke");
    expect(session?.collapsed).toBe(false);
  });

  it("marks cancelled on ExecutionCancelled", () => {
    apply({ type: "ExecutionCancelled", sessionId });
    const session = store.getSession(sessionId);
    expect(session?.status).toBe("cancelled");
    expect(session?.completedAt).toBeDefined();
  });

  it("tracks file counts from capability names", () => {
    apply({ type: "StepScheduled", sessionId, toolName: "file.create", capability: "file.create" });
    apply({ type: "StepCompleted", sessionId, toolName: "file.create", success: true, duration: 100 });
    apply({ type: "StepScheduled", sessionId, toolName: "file.read", capability: "file.read" });
    apply({ type: "StepCompleted", sessionId, toolName: "file.read", success: true, duration: 100 });
    apply({ type: "ExecutionCompleted", sessionId, success: true, summary: "Done", durationMs: 1000 });
    const session = store.getSession(sessionId);
    expect(session?.metadata.filesCreated).toBe(1);
    expect(session?.metadata.filesRead).toBe(1);
  });
});

describe("generateSummary", () => {
  it("generates summary for file operations", () => {
    const session = {
      steps: [
        { capability: "file.create", status: "completed" },
        { capability: "file.read", status: "completed" },
        { capability: "file.create", status: "completed" },
      ],
      durationMs: 12300,
    } as any;
    const summary = generateSummary(session);
    expect(summary).toContain("Created 2 files");
    expect(summary).toContain("Read 1 file");
    expect(summary).toContain("12.3s");
  });

  it("generates summary for tool execution without files", () => {
    const session = {
      steps: [
        { capability: "compute.analyze", status: "completed" },
        { capability: "compute.analyze", status: "completed" },
      ],
      durationMs: 5000,
    } as any;
    const summary = generateSummary(session);
    expect(summary).toContain("Executed 2 tools");
    expect(summary).toContain("5.0s");
  });

  it("returns fallback for empty steps and no duration", () => {
    const session = { steps: [] } as any;
    expect(generateSummary(session)).toBe("No actions recorded");
  });
});
