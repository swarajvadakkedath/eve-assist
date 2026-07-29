import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CommandErrorState from "./CommandErrorState";

describe("CommandErrorState", () => {
  it("renders error message", () => {
    render(<CommandErrorState error="Something went wrong" />);
    expect(screen.getByText("Something went wrong")).toBeInTheDocument();
  });

  it("renders retry button", () => {
    render(<CommandErrorState error="Error" onRetry={() => {}} />);
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("has role alert", () => {
    render(<CommandErrorState error="Error" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
  });
});
