import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import WorkspaceRegistry from "./WorkspaceRegistry";

function ConversationWorkspace() {
  return <div>Conversation Workspace</div>;
}

function SettingsWorkspace() {
  return <div>Settings Workspace</div>;
}

const workspaces = [
  { id: "conversation", label: "Chat", component: ConversationWorkspace },
  { id: "settings", label: "Settings", component: SettingsWorkspace },
];

describe("WorkspaceRegistry", () => {
  it("renders active workspace component", () => {
    render(<WorkspaceRegistry workspaces={workspaces} activeId="conversation" />);
    expect(screen.getByText("Conversation Workspace")).toBeInTheDocument();
  });

  it("renders different workspace on id change", () => {
    render(<WorkspaceRegistry workspaces={workspaces} activeId="settings" />);
    expect(screen.getByText("Settings Workspace")).toBeInTheDocument();
  });

  it("renders fallback for unknown workspace", () => {
    render(<WorkspaceRegistry workspaces={workspaces} activeId="unknown" />);
    expect(screen.getByText(/Unknown workspace: unknown/)).toBeInTheDocument();
  });

  it("renders custom fallback", () => {
    function CustomFallback({ workspaceId }: { workspaceId: string }) {
      return <div>Custom: {workspaceId}</div>;
    }
    render(
      <WorkspaceRegistry
        workspaces={workspaces}
        activeId="nonexistent"
        fallback={CustomFallback}
      />,
    );
    expect(screen.getByText("Custom: nonexistent")).toBeInTheDocument();
  });
});
