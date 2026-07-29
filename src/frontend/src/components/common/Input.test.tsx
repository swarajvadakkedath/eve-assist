import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Input from "./Input";

describe("Input", () => {
  it("renders an input element", () => {
    render(<Input />);
    expect(screen.getByRole("textbox")).toBeInTheDocument();
  });

  it("renders label when provided", () => {
    render(<Input label="Username" />);
    expect(screen.getByLabelText("Username")).toBeInTheDocument();
  });

  it("renders error message when provided", () => {
    render(<Input error="This field is required" />);
    expect(screen.getByRole("alert")).toHaveTextContent("This field is required");
  });

  it("sets aria-invalid when error is provided", () => {
    render(<Input error="Error" />);
    expect(screen.getByRole("textbox")).toHaveAttribute("aria-invalid", "true");
  });

  it("renders hint when provided and no error", () => {
    render(<Input hint="Enter your username" />);
    expect(screen.getByText("Enter your username")).toBeInTheDocument();
  });

  it("does not render hint when error is present", () => {
    render(<Input hint="Hint text" error="Error text" />);
    expect(screen.queryByText("Hint text")).not.toBeInTheDocument();
  });

  it("applies error class when error is provided", () => {
    render(<Input error="Error" />);
    expect(screen.getByRole("textbox").className).toContain("pr-input-error");
  });

  it("calls onChange when value changes", async () => {
    const onChange = vi.fn();
    render(<Input onChange={onChange} />);
    const input = screen.getByRole("textbox");
    await userEvent.type(input, "a");
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("forwards ref", () => {
    const ref = { current: null as HTMLInputElement | null };
    render(<Input ref={ref} />);
    expect(ref.current).toBeInstanceOf(HTMLInputElement);
  });

  it("uses provided id", () => {
    render(<Input id="my-id" label="Name" />);
    expect(screen.getByLabelText("Name")).toHaveAttribute("id", "my-id");
  });

  it("applies custom className", () => {
    render(<Input className="custom" />);
    expect(screen.getByRole("textbox").className).toContain("custom");
  });
});
