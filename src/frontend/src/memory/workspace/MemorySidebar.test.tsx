import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemorySidebar } from "./MemorySidebar";

describe("MemorySidebar", () => {
  const defaultSections = [
    { id: "recent", label: "Recent", icon: "🕐", count: 10 },
    { id: "pinned", label: "Pinned", icon: "📌", count: 3 },
    { id: "explorer", label: "Explorer", icon: "🗂" },
  ];

  it("renders as aside with navigation label", () => {
    render(
      <MemorySidebar
        sections={defaultSections}
        activeSection="recent"
        onSectionChange={vi.fn()}
      />
    );
    expect(screen.getByRole("complementary")).toHaveAttribute("aria-label", "Memory navigation");
  });

  it("renders section labels", () => {
    render(
      <MemorySidebar
        sections={defaultSections}
        activeSection="recent"
        onSectionChange={vi.fn()}
      />
    );
    expect(screen.getByText("Recent")).toBeInTheDocument();
    expect(screen.getByText("Pinned")).toBeInTheDocument();
    expect(screen.getByText("Explorer")).toBeInTheDocument();
  });

  it("renders section counts", () => {
    render(
      <MemorySidebar
        sections={defaultSections}
        activeSection="recent"
        onSectionChange={vi.fn()}
      />
    );
    expect(screen.getByLabelText("10 items")).toBeInTheDocument();
    expect(screen.getByLabelText("3 items")).toBeInTheDocument();
  });

  it("highlights active section", () => {
    render(
      <MemorySidebar
        sections={defaultSections}
        activeSection="pinned"
        onSectionChange={vi.fn()}
      />
    );
    const items = screen.getAllByRole("button");
    expect(items[1].className).toContain("active");
  });

  it("calls onSectionChange when section clicked", async () => {
    const onSectionChange = vi.fn();
    render(
      <MemorySidebar
        sections={defaultSections}
        activeSection="recent"
        onSectionChange={onSectionChange}
      />
    );
    await userEvent.click(screen.getByText("Pinned"));
    expect(onSectionChange).toHaveBeenCalledWith("pinned");
  });

  it("renders search input", () => {
    render(
      <MemorySidebar
        sections={defaultSections}
        activeSection="recent"
        onSectionChange={vi.fn()}
      />
    );
    expect(screen.getByLabelText("Search memory")).toBeInTheDocument();
  });

  it("calls onSearch when search input changes", async () => {
    const onSearch = vi.fn();
    render(
      <MemorySidebar
        sections={defaultSections}
        activeSection="recent"
        onSectionChange={vi.fn()}
        onSearch={onSearch}
      />
    );
    const input = screen.getByLabelText("Search memory");
    await userEvent.type(input, "test");
    expect(onSearch).toHaveBeenCalledWith("test");
  });
});
