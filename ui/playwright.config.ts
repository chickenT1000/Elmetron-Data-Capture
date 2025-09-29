import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './playwright',
  fullyParallel: true,
  workers: process.env.CI ? 2 : undefined,
  reporter: [['list'], process.env.CI ? ['html', { open: 'never' }] : ['html']],
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
