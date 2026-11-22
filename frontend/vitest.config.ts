import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov"],
      include: ["src/lib/**", "src/features/**", "src/app/**"],
      exclude: ["src/**/*.test.ts", "src/**/*.test.tsx", "src/test/**"],
      thresholds: { statements: 60, branches: 50, functions: 60, lines: 70 },
    },
  },
});
