import { expect, test } from '@playwright/test';

const stories = [
  {
    id: 'foundation-typography--overview',
    name: 'foundation-typography-overview.png',
  },
  {
    id: 'dashboard-measurementpanel--ready',
    name: 'measurement-panel-ready.png',
  },
  {
    id: 'dashboard-measurementpanel--offline',
    name: 'measurement-panel-offline.png',
  },
  {
    id: 'dashboard-measurementpanel--error',
    name: 'measurement-panel-error.png',
  },
  {
    id: 'dashboard-commandhistory--default',
    name: 'command-history-default.png',
  },
  {
    id: 'dashboard-logfeed--with-entries',
    name: 'log-feed-with-entries.png',
  },
  {
    id: 'dashboard-overview--default',
    name: 'dashboard-overview-default.png',
  },
  {
    id: 'dashboard-overview--errors',
    name: 'dashboard-overview-errors.png',
  },
];

test.describe('Storybook visual', () => {
  for (const story of stories) {
    test(`${story.id} matches baseline`, async ({ page }) => {
      await page.goto(`/iframe.html?id=${story.id}&args=&viewMode=story`);
      await page.setViewportSize({ width: 1280, height: 720 });
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(200);
      await expect(page).toHaveScreenshot(story.name, {
        maxDiffPixels: 150,
      });
    });
  }
});
