import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SidebarItem from "./SidebarItem";

describe("SidebarItem", () => {
  it("renders label", () => {
    render(<SidebarItem label="Chat" />);
    expect(screen.getByText("Chat")).toBeInTheDocument();
  });

  it("renders icon when provided", () => {
    render(<SidebarItem label="Chat" icon={<span data-testid="icon" />} />);
    expect(screen.getByTestId("icon")).toBeInTheDocument();
  });

  it("sets aria-current when active", () => {
    render(<SidebarItem label="Chat" active />);
    expect(screen.getByRole("menuitem")).toHaveAttribute("aria-current", "page");
  });

  it("does not set aria-current when not active", () => {
    render(<SidebarItem label="Chat" />);
    expect(screen.getByRole("menuitem")).not.toHaveAttribute("aria-current");
  });

  it("shows badge when provided", () => {
    render(<SidebarItem label="Chat" badge={5} />);
    expect(screen.getByText("5")).toBeInTheDocument();
  });

  it("calls onClick when clicked", async () => {
    const onClick = vi.fn();
    render(<SidebarItem label="Chat" onClick={onClick} />);
    await userEvent.click(screen.getByRole("menuitem"));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it("sets aria-label", () => {
    render(<SidebarItem label="Chat" />);
    expect(screen.getByRole("menuitem")).toHaveAttribute("aria-label", "Chat");
  });
});
