import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  waitForReady,
  startStatusPolling,
  stopStatusPolling,
  getStatusSnapshot,
  _resetForTests,
} from "./statusStore";

beforeEach(() => {
  _resetForTests();
  vi.useFakeTimers();
});

afterEach(() => {
  _resetForTests();
  vi.useRealTimers();
});

function mockFetchSequence(responses: { status: number; body: any }[]) {
  let call = 0;
  globalThis.fetch = vi.fn().mockImplementation(async () => {
    const res = responses[Math.min(call++, responses.length - 1)];
    return {
      ok: res.status < 400,
      status: res.status,
      json: async () => res.body,
    };
  });
}

describe("statusStore", () => {
  it("starts in starting state", () => {
    mockFetchSequence([]);
    const s = getStatusSnapshot();
    expect(s.status).toBe("starting");
    expect(s.ready).toBe(false);
  });

  it("polls /desktop/status and updates state", async () => {
    mockFetchSequence([
      { status: 200, body: { status: "initializing", metadata: {} } },
      { status: 200, body: { status: "ready", metadata: {} } },
    ]);
    startStatusPolling();
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1000);
    expect(globalThis.fetch).toHaveBeenCalledTimes(2);
    const s = getStatusSnapshot();
    expect(s.status).toBe("ready");
    expect(s.ready).toBe(true);
  });

  it("waitForReady resolves when ready", async () => {
    mockFetchSequence([
      { status: 200, body: { status: "starting", metadata: {} } },
      { status: 200, body: { status: "ready", metadata: {} } },
    ]);
    startStatusPolling();
    let resolved = false;
    const p = waitForReady().then(() => { resolved = true; });
    await vi.advanceTimersByTimeAsync(1000);
    await p;
    expect(resolved).toBe(true);
  });

  it("waitForReady resolves immediately when already ready", async () => {
    mockFetchSequence([{ status: 200, body: { status: "ready", metadata: {} } }]);
    startStatusPolling();
    await vi.advanceTimersByTimeAsync(100);
    const snap = getStatusSnapshot();
    expect(snap.ready).toBe(true);
    // Now waitForReady should resolve immediately
    let resolved = false;
    await waitForReady().then(() => { resolved = true; });
    expect(resolved).toBe(true);
  });

  it("waitForReady rejects on timeout", async () => {
    // Use a backend that never becomes ready.
    mockFetchSequence([{ status: 200, body: { status: "starting", metadata: {} } }]);
    startStatusPolling();
    // Force the first poll to complete so status is definitely "starting".
    await vi.advanceTimersByTimeAsync(100);
    const p = waitForReady(500);
    await vi.advanceTimersByTimeAsync(600);
    await expect(p).rejects.toThrow("Backend not ready after 500ms");
  });

  it("no duplicate pollers on multiple start() calls", () => {
    mockFetchSequence([{ status: 200, body: { status: "ready", metadata: {} } }]);
    startStatusPolling();
    startStatusPolling();
    expect(globalThis.fetch).toHaveBeenCalledTimes(1);
  });

  it("stop clears poller", async () => {
    mockFetchSequence([
      { status: 200, body: { status: "starting", metadata: {} } },
    ]);
    startStatusPolling();
    stopStatusPolling();
    await vi.advanceTimersByTimeAsync(5000);
    expect(globalThis.fetch).toHaveBeenCalledTimes(1); // only the initial poll
  });

  it("fetch uses raw fetch, not api module", async () => {
    mockFetchSequence([{ status: 200, body: { status: "ready", metadata: {} } }]);
    startStatusPolling();
    const calledUrl = (globalThis.fetch as any).mock.calls[0][0];
    expect(calledUrl).toContain("/desktop/status");
  });
});
