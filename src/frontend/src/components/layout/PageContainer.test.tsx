import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import PageContainer from "./PageContainer";

describe("PageContainer", () => {
  it("renders children", () => {
    render(<PageContainer><main data-testid="content" /></PageContainer>);
    expect(screen.getByTestId("content")).toBeInTheDocument();
  });

  it("renders region landmark", () => {
    render(<PageContainer>Content</PageContainer>);
    expect(screen.getByRole("region")).toBeInTheDocument();
  });

  it("applies full class when full prop is true", () => {
    const { container } = render(<PageContainer full>Content</PageContainer>);
    expect(container.firstElementChild?.className).toContain("pr-page-container-full");
  });

  it("applies custom className", () => {
    const { container } = render(<PageContainer className="custom">Content</PageContainer>);
    expect(container.firstElementChild?.className).toContain("custom");
  });
});
