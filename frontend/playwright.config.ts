import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

const evidenceDirectory = path.resolve(
  process.env.FLOWSTEAD_EVIDENCE_DIR || "../docs/design/evidence",
);

/** Optional executable override for local runs; empty/whitespace/unset keeps `channel: 'chromium'`. */
const chromiumExecutablePath =
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?.trim() || undefined;
const chromiumLaunch = chromiumExecutablePath
  ? { launchOptions: { executablePath: chromiumExecutablePath } }
  : { channel: "chromium" as const };

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  outputDir: path.join(evidenceDirectory, "playwright-test-results"),
  reporter: [
    [
      "html",
      {
        outputFolder: path.join(evidenceDirectory, "playwright-report"),
        open: "never",
      },
    ],
    [
      "json",
      {
        outputFile: path.join(
          evidenceDirectory,
          "playwright-report",
          "results.json",
        ),
      },
    ],
  ],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:5173",
    ...chromiumLaunch,
    trace: "off",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: "pnpm run dev --host 127.0.0.1",
    url: "http://127.0.0.1:5173/plants",
    reuseExistingServer: false,
    timeout: 30_000,
  },
  projects: [
    {
      name: "desktop",
      use: {
        ...devices["Desktop Chrome"],
        viewport: { width: 1330, height: 900 },
      },
    },
    {
      name: "mobile",
      use: {
        ...devices["Pixel 5"],
        viewport: { width: 390, height: 844 },
        isMobile: true,
      },
    },
  ],
});
