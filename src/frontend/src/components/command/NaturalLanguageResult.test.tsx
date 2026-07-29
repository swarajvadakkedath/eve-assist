import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import NaturalLanguageResult from "./NaturalLanguageResult";
import type { NaturalLanguageIntent } from "./types";

const intent: NaturalLanguageIntent = {
  text: "Open the settings panel",
  intent: "navigate_to_settings",
  confidence: 0.87,
  resultType: "open-panel",
  suggestedCommand: {
    id: "settings", name: "Settings", description: "Open settings", category: "app", resultType: "open-panel", action: () => {},
  },
};

describe("NaturalLanguageResult", () => {
  it("renders intent and confidence", () => {
    render(<NaturalLanguageResult intent={intent} onExecute={() => {}} />);
    expect(screen.getByText("navigate_to_settings")).toBeInTheDocument();
    expect(screen.getByText("87%")).toBeInTheDocument();
  });

  it("renders NL badge", () => {
    render(<NaturalLanguageResult intent={intent} onExecute={() => {}} />);
    expect(screen.getByText("NL")).toBeInTheDocument();
  });

  it("renders execute button", () => {
    render(<NaturalLanguageResult intent={intent} onExecute={() => {}} />);
    expect(screen.getByText("Execute")).toBeInTheDocument();
  });
});
