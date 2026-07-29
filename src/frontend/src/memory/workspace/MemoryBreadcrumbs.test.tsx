import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryBreadcrumbs } from "./MemoryBreadcrumbs";

describe("MemoryBreadcrumbs", () => {
  it("returns null with empty items", () => {
    const { container } = render(<MemoryBreadcrumbs items={[]} />);
    expect(container.firstChild).toBeNull();
  });

  it("renders breadcrumb items", () => {
    const items = [{ label: "Memory", id: "memory" }, { label: "Recent", id: "recent" }];
    render(<MemoryBreadcrumbs items={items} />);
    expect(screen.getByText("Memory")).toBeInTheDocument();
    expect(screen.getByText("Recent")).toBeInTheDocument();
  });

  it("has navigation role with aria-label", () => {
    const items = [{ label: "Memory", id: "memory" }];
    render(<MemoryBreadcrumbs items={items} />);
    expect(screen.getByRole("navigation")).toHaveAttribute("aria-label", "Breadcrumb");
  });

  it("marks last item as current page", () => {
    const items = [{ label: "Memory", id: "memory" }, { label: "Recent", id: "recent" }];
    render(<MemoryBreadcrumbs items={items} />);
    expect(screen.getByText("Recent")).toHaveAttribute("aria-current", "page");
  });

  it("calls onNavigate when non-last item clicked", async () => {
    const onNavigate = vi.fn();
    const items = [
      { label: "Memory", id: "memory" },
      { label: "Recent", id: "recent" },
      { label: "Knowledge", id: "knowledge" },
    ];
    render(<MemoryBreadcrumbs items={items} onNavigate={onNavigate} />);
    await userEvent.click(screen.getByText("Recent"));
    expect(onNavigate).toHaveBeenCalledWith(items[1]);
  });

  it("renders separator between items", () => {
    const items = [{ label: "A", id: "a" }, { label: "B", id: "b" }];
    render(<MemoryBreadcrumbs items={items} />);
    const separators = screen.getAllByText("/");
    expect(separators).toHaveLength(1);
  });
});
