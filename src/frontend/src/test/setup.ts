import "@testing-library/jest-dom/vitest";

HTMLDivElement.prototype.scrollIntoView = vi.fn();
HTMLDivElement.prototype.scrollBy = vi.fn();
window.HTMLElement.prototype.scrollIntoView = vi.fn();
