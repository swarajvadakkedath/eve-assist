import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Sidebar from "./Sidebar";

const mockSections = [
  {
    label: "Main",
    items: [
      { id: "chat", label: "Chat", icon: "💬" },
      { id: "memory", label: "Memory", icon: "🧠", badge: 3 },
    ],
  },
  {
    items: [
      { id: "settings", label: "Settings", icon: "⚙", disabled: true },
    ],
  },
];

describe("Sidebar", () => {
  it("renders nav items", () => {
    render(<Sidebar sections={mockSections} />);
    expect(screen.getByText("Chat")).toBeInTheDocument();
    expect(screen.getByText("Memory")).toBeInTheDocument();
  });

  it("renders section labels", () => {
    render(<Sidebar sections={mockSections} />);
    expect(screen.getByText("Main")).toBeInTheDocument();
  });

  it("marks active item with aria-current", () => {
    render(<Sidebar sections={mockSections} activeId="chat" />);
    expect(screen.getByText("Chat").closest("[aria-current]")).toHaveAttribute("aria-current", "page");
  });

  it("does not mark inactive items", () => {
    render(<Sidebar sections={mockSections} activeId="chat" />);
    expect(screen.getByText("Memory").closest("[aria-current]")).toBeNull();
  });

  it("disables disabled items", () => {
    render(<Sidebar sections={mockSections} />);
    expect(screen.getByText("Settings").closest("button")).toBeDisabled();
  });

  it("calls onNavigate when item clicked", async () => {
    const onNavigate = vi.fn();
    render(<Sidebar sections={mockSections} onNavigate={onNavigate} />);
    await userEvent.click(screen.getByText("Chat"));
    expect(onNavigate).toHaveBeenCalledWith("chat");
  });

  it("renders collapsed without labels", () => {
    const { container } = render(<Sidebar sections={mockSections} collapsed />);
    expect(container.querySelector(".pr-sidebar-item-label")).toBeNull();
  });

  it("calls onToggleCollapse when toggle clicked", async () => {
    const onToggle = vi.fn();
    render(<Sidebar sections={mockSections} onToggleCollapse={onToggle} />);
    await userEvent.click(screen.getByLabelText("Collapse sidebar"));
    expect(onToggle).toHaveBeenCalledOnce();
  });

  it("renders navigation landmark", () => {
    render(<Sidebar sections={mockSections} />);
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });
});
