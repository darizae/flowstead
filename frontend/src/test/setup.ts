import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

// Ensure React Testing Library unmounts and clears the DOM between tests so
// renders cannot leak into later assertions.
afterEach(() => {
  cleanup();
});
