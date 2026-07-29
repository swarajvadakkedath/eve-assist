import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import MarkdownRenderer from "./MarkdownRenderer";

describe("MarkdownRenderer", () => {
  it("renders plain text", () => {
    render(<MarkdownRenderer content="Hello world" />);
    expect(screen.getByText("Hello world")).toBeInTheDocument();
  });

  it("returns null for empty content", () => {
    const { container } = render(<MarkdownRenderer content="" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders bold text", () => {
    render(<MarkdownRenderer content="This is **bold** text" />);
    const el = screen.getByText("bold");
    expect(el.tagName).toBe("STRONG");
  });

  it("renders italic text", () => {
    render(<MarkdownRenderer content="This is *italic* text" />);
    const el = screen.getByText("italic");
    expect(el.tagName).toBe("EM");
  });

  it("renders inline code", () => {
    render(<MarkdownRenderer content="Use `code` here" />);
    const el = screen.getByText("code");
    expect(el.tagName).toBe("CODE");
  });

  it("renders paragraph", () => {
    render(<MarkdownRenderer content={"Hello\n\nWorld"} />);
    expect(screen.getByText("Hello")).toBeInTheDocument();
    expect(screen.getByText("World")).toBeInTheDocument();
  });

  it("renders unordered list", () => {
    render(<MarkdownRenderer content={"- Item A\n- Item B"} />);
    expect(screen.getByText("Item A")).toBeInTheDocument();
    expect(screen.getByText("Item B")).toBeInTheDocument();
  });

  it("renders ordered list", () => {
    render(<MarkdownRenderer content={"1. First\n2. Second"} />);
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });

  it("renders code block", () => {
    render(<MarkdownRenderer content={"```ts\nconst x = 1;\n```"} />);
    expect(screen.getByText("ts")).toBeInTheDocument();
    expect(screen.getByText("const x = 1;")).toBeInTheDocument();
  });

  it("renders streaming cursor when streaming", () => {
    const { container } = render(<MarkdownRenderer content="Hello" streaming />);
    expect(container.querySelector(".pr-streaming-cursor")).toBeInTheDocument();
  });
});
