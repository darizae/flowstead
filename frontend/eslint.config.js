import js from "@eslint/js";
import tseslint from "typescript-eslint";
import reactHooks from "eslint-plugin-react-hooks";
import globals from "globals";

export default tseslint.config(
  {
    ignores: [
      "dist/**",
      "node_modules/**",
      "playwright-report/**",
      "test-results/**",
      // Auto-generated from the backend OpenAPI contract (audit #29)
      "src/lib/api/generated/**",
    ],
  },
  js.configs.recommended,
  {
    languageOptions: { globals: { ...globals.browser, ...globals.node } },
  },
  ...tseslint.configs.recommended,
  {
    files: ["**/*.{ts,tsx}"],
    plugins: { "react-hooks": reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-explicit-any": "warn",
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
    },
  },
  {
    files: ["e2e/**", "src/lib/exports/csv.ts", "src/lib/exports/csv.test.ts"],
    rules: {
      // Legacy regexes deliberately escape quotes/control bytes in generated CSV and E2E inputs.
      "no-useless-escape": "off",
      "no-control-regex": "off",
    },
  },
);
