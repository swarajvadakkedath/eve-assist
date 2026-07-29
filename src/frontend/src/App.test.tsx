import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "./App";

vi.mock("./services/voice", () => ({
  voiceService: {
    connect: vi.fn().mockResolvedValue(undefined),
    disconnect: vi.fn(),
    stopListening: vi.fn().mockResolvedValue(undefined),
    startSession: vi.fn().mockResolvedValue(undefined),
    startListening: vi.fn().mockResolvedValue(undefined),
    on: vi.fn().mockReturnValue(vi.fn()),
    emit: vi.fn(),
    state: {
      isListening: false,
      isSpeaking: false,
      state: "idle",
      sessionId: "",
      conversationId: "",
      currentTranscript: "",
      audioLevel: 0,
    },
  },
}));

const mockFetch = vi.fn().mockResolvedValue({
  ok: true,
  json: vi.fn().mockResolvedValue({ conversations: [] }),
  text: vi.fn().mockResolvedValue(""),
});
vi.stubGlobal("fetch", mockFetch);

describe("App", () => {
  beforeEach(() => {
    render(<App />);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders without crashing", () => {
    expect(screen.getByTitle("Commands (Ctrl+K)")).toBeInTheDocument();
  });

  it("renders conversation view", () => {
    expect(screen.getByRole("textbox", { name: "Message input" })).toBeInTheDocument();
  });
});
