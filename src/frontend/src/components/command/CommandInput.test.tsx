import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import CommandInput from "./CommandInput";

describe("CommandInput", () => {
  it("renders with placeholder", () => {
    render(
      <CommandInput value="" onChange={() => {}} onKeyDown={() => {}} inputRef={{ current: null }} />
    );
    expect(screen.getByPlaceholderText("Type a command or search...")).toBeInTheDocument();
  });

  it("displays current value", () => {
    render(
      <CommandInput value="test" onChange={() => {}} onKeyDown={() => {}} inputRef={{ current: null }} />
    );
    const input = screen.getByLabelText("Command search") as HTMLInputElement;
    expect(input.value).toBe("test");
  });

  it("shows clear button when value is not empty", () => {
    render(
      <CommandInput value="test" onChange={() => {}} onKeyDown={() => {}} inputRef={{ current: null }} />
    );
    expect(screen.getByLabelText("Clear search")).toBeInTheDocument();
  });

  it("hides clear button when value is empty", () => {
    render(
      <CommandInput value="" onChange={() => {}} onKeyDown={() => {}} inputRef={{ current: null }} />
    );
    expect(screen.queryByLabelText("Clear search")).not.toBeInTheDocument();
  });
});
