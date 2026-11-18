import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  outputDir: '../docs/design/evidence/playwright-test-results',
  reporter: [['html', { outputFolder: '../docs/design/evidence/playwright-report', open: 'never' }]],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:5173',
    channel: 'chromium',
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
    { name: 'desktop', use: { ...devices['Desktop Chrome'], viewport: { width: 1330, height: 900 }, channel: 'chromium' } },
    { name: 'mobile', use: { ...devices['Pixel 5'], viewport: { width: 390, height: 844 }, isMobile: true, channel: 'chromium' } },
  ],
});
