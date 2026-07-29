import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryFilters } from "./MemoryFilters";

describe("MemoryFilters", () => {
  const defaultFilters = {
    superTypes: [] as any[],
    statuses: [] as any[],
    tags: [] as string[],
    pinned: undefined as boolean | undefined,
    dateFrom: undefined as number | undefined,
    dateTo: undefined as number | undefined,
  };

  it("renders filter region", () => {
    render(<MemoryFilters filters={defaultFilters} onChange={vi.fn()} availableTags={[]} />);
    expect(screen.getByRole("region")).toHaveAttribute("aria-label", "Filters");
  });

  it("renders super type filter buttons", () => {
    render(<MemoryFilters filters={defaultFilters} onChange={vi.fn()} availableTags={[]} />);
    expect(screen.getByText("Action")).toBeInTheDocument();
    expect(screen.getByText("Knowledge")).toBeInTheDocument();
    expect(screen.getByText("Entity")).toBeInTheDocument();
    expect(screen.getByText("Meta")).toBeInTheDocument();
  });

  it("renders status filter buttons", () => {
    render(<MemoryFilters filters={defaultFilters} onChange={vi.fn()} availableTags={[]} />);
    expect(screen.getByText("Active")).toBeInTheDocument();
    expect(screen.getByText("Archived")).toBeInTheDocument();
  });

  it("toggles super type filter on click", async () => {
    const onChange = vi.fn();
    render(<MemoryFilters filters={defaultFilters} onChange={onChange} availableTags={[]} />);
    await userEvent.click(screen.getByLabelText("Filter by Knowledge"));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ superTypes: ["knowledge"] })
    );
  });

  it("renders available tags as filter buttons", () => {
    render(
      <MemoryFilters
        filters={defaultFilters}
        onChange={vi.fn()}
        availableTags={["tag1", "tag2"]}
      />
    );
    expect(screen.getByLabelText("Filter by tag tag1")).toBeInTheDocument();
    expect(screen.getByLabelText("Filter by tag tag2")).toBeInTheDocument();
  });

  it("renders pinned filter button", () => {
    render(<MemoryFilters filters={defaultFilters} onChange={vi.fn()} availableTags={[]} />);
    expect(screen.getByLabelText("Filter pinned items only")).toBeInTheDocument();
  });

  it("toggles pinned filter", async () => {
    const onChange = vi.fn();
    render(<MemoryFilters filters={defaultFilters} onChange={onChange} availableTags={[]} />);
    await userEvent.click(screen.getByLabelText("Filter pinned items only"));
    expect(onChange).toHaveBeenCalledWith(
      expect.objectContaining({ pinned: true })
    );
  });
});
