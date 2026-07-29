import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CommandFooter from "./CommandFooter";

describe("CommandFooter", () => {
  it("renders navigation tips", () => {
    render(<CommandFooter totalResults={0} selectedIndex={0} hasQuery={false} />);
    expect(screen.getByText("close")).toBeInTheDocument();
  });

  it("shows result count when hasQuery is true", () => {
    render(<CommandFooter totalResults={5} selectedIndex={0} hasQuery={true} />);
    expect(screen.getByText("5 results")).toBeInTheDocument();
  });

  it("shows singular result count", () => {
    render(<CommandFooter totalResults={1} selectedIndex={0} hasQuery={true} />);
    expect(screen.getByText("1 result")).toBeInTheDocument();
  });

  it("hides count when no query", () => {
    render(<CommandFooter totalResults={3} selectedIndex={0} hasQuery={false} />);
    expect(screen.queryByText("3 results")).not.toBeInTheDocument();
  });
});
