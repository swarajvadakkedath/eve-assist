import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CommandCategory from "./CommandCategory";

describe("CommandCategory", () => {
  it("renders label", () => {
    render(<CommandCategory label="Applications" />);
    expect(screen.getByText("Applications")).toBeInTheDocument();
  });

  it("renders count when provided", () => {
    render(<CommandCategory label="Apps" count={3} />);
    expect(screen.getByText("3")).toBeInTheDocument();
  });

  it("has role presentation", () => {
    render(<CommandCategory label="Apps" />);
    expect(screen.getByRole("presentation")).toBeInTheDocument();
  });
});
