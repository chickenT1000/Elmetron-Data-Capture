import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './acceptance',
  workers: 1,
  timeout: 60_000,
  reporter: [['list'], ['html', { outputFolder: 'playwright-report', open: 'never' }]],
  use: {
    ...devices['Desktop Chrome'],
    baseURL: 'http://127.0.0.1:18052',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  webServer: {
    command: 'uv run python -m elmetron.cli.app --data-dir validation/playwright-home serve --port 18052',
    cwd: '..',
    url: 'http://127.0.0.1:18052/health',
    reuseExistingServer: false,
    gracefulShutdown: { signal: 'SIGTERM', timeout: 20_000 },
  },
});
