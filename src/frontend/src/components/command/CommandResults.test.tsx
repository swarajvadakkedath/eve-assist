import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CommandResults from "./CommandResults";
import type { CommandGroup } from "./types";

const groups: CommandGroup[] = [
  {
    label: "Apps",
    commands: [
      { id: "a1", name: "Settings", description: "Open settings", category: "app", resultType: "open-panel", action: () => {} },
      { id: "a2", name: "Themes", description: "Manage themes", category: "app", resultType: "run-command", action: () => {} },
    ],
  },
  {
    label: "Tools",
    commands: [
      { id: "t1", name: "Search", description: "Search tool", category: "tool", resultType: "search-query", action: () => {} },
    ],
  },
];

describe("CommandResults", () => {
  it("renders grouped results", () => {
    render(
      <CommandResults
        groups={groups}
        selectedIndex={0}
        onSelect={() => {}}
        onHover={() => {}}
        loading={false}
        error={null}
        query=""
      />
    );
    expect(screen.getByText("Apps")).toBeInTheDocument();
    expect(screen.getByText("Tools")).toBeInTheDocument();
    expect(screen.getByText("Settings")).toBeInTheDocument();
    expect(screen.getByText("Search")).toBeInTheDocument();
  });

  it("focuses selected item", () => {
    render(
      <CommandResults
        groups={groups}
        selectedIndex={1}
        onSelect={() => {}}
        onHover={() => {}}
        loading={false}
        error={null}
        query=""
      />
    );
    const items = screen.getAllByRole("option");
    expect(items[1]).toHaveAttribute("aria-selected", "true");
  });

  it("shows loading state", () => {
    render(
      <CommandResults
        groups={[]}
        selectedIndex={0}
        onSelect={() => {}}
        onHover={() => {}}
        loading={true}
        error={null}
        query=""
      />
    );
    expect(screen.getByText("Searching...")).toBeInTheDocument();
  });

  it("shows error state", () => {
    render(
      <CommandResults
        groups={[]}
        selectedIndex={0}
        onSelect={() => {}}
        onHover={() => {}}
        loading={false}
        error="Failed to search"
        query=""
      />
    );
    expect(screen.getByText("Failed to search")).toBeInTheDocument();
  });

  it("shows empty state when no results", () => {
    render(
      <CommandResults
        groups={[]}
        selectedIndex={0}
        onSelect={() => {}}
        onHover={() => {}}
        loading={false}
        error={null}
        query="test"
      />
    );
    expect(screen.getByText(/No results for/)).toBeInTheDocument();
  });

  it("has listbox role", () => {
    render(
      <CommandResults
        groups={groups}
        selectedIndex={0}
        onSelect={() => {}}
        onHover={() => {}}
        loading={false}
        error={null}
        query=""
      />
    );
    expect(screen.getByRole("listbox")).toBeInTheDocument();
  });
});
