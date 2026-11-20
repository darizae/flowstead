import { defineConfig, devices } from '@playwright/test';

/** Optional executable override for local runs; empty/whitespace/unset keeps `channel: 'chromium'`. */
const chromiumExecutablePath = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH?.trim() || undefined;
const chromiumLaunch = chromiumExecutablePath
  ? { launchOptions: { executablePath: chromiumExecutablePath } }
  : { channel: 'chromium' as const };

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  outputDir: '../docs/design/evidence/playwright-test-results',
  reporter: [
    ['html', { outputFolder: '../docs/design/evidence/playwright-report', open: 'never' }],
    ['json', { outputFile: '../docs/design/evidence/playwright-report/results.json' }],
  ],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:5173',
    ...chromiumLaunch,
    trace: 'off',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'npm run dev -- --host 127.0.0.1',
    url: 'http://127.0.0.1:5173/plants',
    reuseExistingServer: false,
    timeout: 30_000,
  },
  projects: [
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1330, height: 900 } } },
    { name: 'mobile', use: { ...devices['Pixel 5'], viewport: { width: 390, height: 844 }, isMobile: true } },
  ],
});
