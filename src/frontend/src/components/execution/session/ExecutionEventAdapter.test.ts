import { describe, it, expect } from "vitest";
import { adaptBackendEvent, createCompletedEvent } from "./ExecutionEventAdapter";

describe("ExecutionEventAdapter", () => {
  const convId = "c1";
  const reqId = "req-1";
  const request = "Read my files";

  it("adapts planner_started to ExecutionStarted", () => {
    const raw = { type: "planner_started", data: { request: "Read my files" } };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    expect(result).toEqual({
      type: "ExecutionStarted",
      sessionId: "s1",
      request: "Read my files",
      conversationId: convId,
      requestId: reqId,
    });
  });

  it("uses fallback request when data.request is empty", () => {
    const raw = { type: "planner_started", data: {} };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    if (result?.type === "ExecutionStarted") {
      expect(result.request).toBe("Read my files");
    }
  });

  it("adapts planner_completed to PlanningCompleted", () => {
    const raw = { type: "planner_completed", data: { steps: 3 } };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    expect(result).toEqual({ type: "PlanningCompleted", sessionId: "s1", steps: 3 });
  });

  it("adapts tool_requested to StepScheduled", () => {
    const raw = { type: "tool_requested", data: { tool_name: "file.read", capability: "file.read" } };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    expect(result).toEqual({ type: "StepScheduled", sessionId: "s1", toolName: "file.read", capability: "file.read" });
  });

  it("falls back to tool_name for capability when missing", () => {
    const raw = { type: "tool_requested", data: { tool_name: "file.read" } };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    expect(result).toEqual({ type: "StepScheduled", sessionId: "s1", toolName: "file.read", capability: "file.read" });
  });

  it("adapts tool_running to StepStarted", () => {
    const raw = { type: "tool_running", data: { tool_name: "file.read" } };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    expect(result).toEqual({ type: "StepStarted", sessionId: "s1", toolName: "file.read" });
  });

  it("adapts tool_completed to StepCompleted", () => {
    const raw = { type: "tool_completed", data: { tool_name: "file.read", success: true, duration: 1500 } };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    expect(result).toEqual({ type: "StepCompleted", sessionId: "s1", toolName: "file.read", success: true, duration: 1500 });
  });

  it("defaults success to true when not provided", () => {
    const raw = { type: "tool_completed", data: { tool_name: "file.read" } };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    if (result?.type === "StepCompleted") {
      expect(result.success).toBe(true);
    }
  });

  it("adapts error to ExecutionFailed", () => {
    const raw = { type: "error", data: { error: "Something broke" } };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    expect(result).toEqual({ type: "ExecutionFailed", sessionId: "s1", error: "Something broke" });
  });

  it("returns null for unknown event types", () => {
    const raw = { type: "unknown_event", data: {} };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    expect(result).toBeNull();
  });

  it("returns null for token events", () => {
    const raw = { type: "token", data: { token: "hello" } };
    const result = adaptBackendEvent(raw, "s1", convId, reqId, request);
    expect(result).toBeNull();
  });

  it("creates ExecutionCompleted via helper", () => {
    const result = createCompletedEvent("s1", true, "All done", 5000);
    expect(result).toEqual({ type: "ExecutionCompleted", sessionId: "s1", success: true, summary: "All done", durationMs: 5000 });
  });
});
