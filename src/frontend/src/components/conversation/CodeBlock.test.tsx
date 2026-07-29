import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CodeBlock from "./CodeBlock";

describe("CodeBlock", () => {
  it("renders language label", () => {
    render(<CodeBlock language="typescript" code="const x = 1;" />);
    expect(screen.getByText("typescript")).toBeInTheDocument();
  });

  it("renders code content", () => {
    render(<CodeBlock language="typescript" code="const x = 1;" />);
    expect(screen.getByText("const x = 1;")).toBeInTheDocument();
  });

  it("renders copy button", () => {
    render(<CodeBlock language="typescript" code="const x = 1;" />);
    expect(screen.getByRole("button", { name: "Copy code" })).toBeInTheDocument();
  });

  it("escapes HTML in code", () => {
    const { container } = render(<CodeBlock language="html" code="<script>alert('xss')</script>" />);
    expect(container.querySelector("code")?.textContent).toBe("&lt;script&gt;alert('xss')&lt;/script&gt;");
  });

  it("shows text fallback for empty language", () => {
    render(<CodeBlock language="" code="some code" />);
    expect(screen.getByText("text")).toBeInTheDocument();
  });
});
