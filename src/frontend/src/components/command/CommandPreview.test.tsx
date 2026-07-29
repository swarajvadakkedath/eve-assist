import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CommandPreview from "./CommandPreview";
import type { CommandPreviewData } from "./types";

const preview: CommandPreviewData = {
  item: { id: "test", name: "Test Cmd", description: "A test", category: "app", resultType: "run-command", action: () => {} },
  description: "A test command",
  category: "app",
  shortcut: "Ctrl+T",
  estimatedAction: "Execute command",
};

describe("CommandPreview", () => {
  it("renders preview details", () => {
    render(<CommandPreview data={preview} />);
    expect(screen.getByText("Test Cmd")).toBeInTheDocument();
    expect(screen.getByText("A test command")).toBeInTheDocument();
    expect(screen.getByText("app")).toBeInTheDocument();
  });

  it("shows shortcut when provided", () => {
    render(<CommandPreview data={preview} />);
    expect(screen.getByText("Ctrl+T")).toBeInTheDocument();
  });

  it("renders empty state when no data", () => {
    render(<CommandPreview data={null} />);
    expect(screen.getByText("Select a command to preview")).toBeInTheDocument();
  });
});
