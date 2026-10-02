import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  webServer: {
    command: 'uv run --directory .. python -m http.server 6006 --bind 127.0.0.1 --directory ui/storybook-static',
    url: 'http://127.0.0.1:6006',
    reuseExistingServer: !process.env.CI,
  },
  testDir: './playwright',
  fullyParallel: true,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['list'], ['html', { open: 'never' }]],
  use: {
    trace: 'on-first-retry',
    screenshot: 'off',
    video: 'off',
    baseURL: process.env.STORYBOOK_BASE_URL ?? 'http://127.0.0.1:6006',
  },
  projects: [
    {
      name: 'chromium',
      use: devices['Desktop Chrome'],
    },
  ],
});
