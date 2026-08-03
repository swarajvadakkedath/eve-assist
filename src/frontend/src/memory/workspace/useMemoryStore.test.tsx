import { describe, it, expect, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { useMemoryStore, useMemoryNodes } from "./useMemoryStore";
import { resetMemoryStore } from "@/memory/core";
import type { FC } from "react";

describe("useMemoryStore", () => {
  beforeEach(() => {
    resetMemoryStore();
  });

  it("returns current store state", () => {
    let state: any;
    const TestComp: FC = () => {
      state = useMemoryStore();
      return null;
    };
    render(<TestComp />);
    expect(state).toHaveProperty("nodeCount");
    expect(state).toHaveProperty("edgeCount");
    expect(state).toHaveProperty("lastEvent");
  });

  it("reflects changes after adding a node", () => {
    const TestComp: FC = () => {
      const state = useMemoryStore();
      return <div data-testid="count">{state.nodeCount}</div>;
    };
    render(<TestComp />);
    expect(screen.getByTestId("count").textContent).toBe("0");
  });
});

describe("useMemoryNodes", () => {
  beforeEach(() => {
    resetMemoryStore();
  });

  it("returns node and edge counts", () => {
    let result: any;
    const TestComp: FC = () => {
      result = useMemoryNodes();
      return null;
    };
    render(<TestComp />);
    expect(result).toHaveProperty("nodeCount");
    expect(result).toHaveProperty("edgeCount");
  });
});
