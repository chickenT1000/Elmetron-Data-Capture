import { expect, test } from '@playwright/test';

const deterministicInitScript = `
  (() => {
    const FIXED_TIME = Date.parse('2024-08-01T15:00:00Z');
    const OriginalDate = Date;
    const FixedDate = class extends OriginalDate {
      constructor(...args) {
        if (args.length === 0) {
          super(FIXED_TIME);
        } else {
          super(...args);
        }
      }
      static now() {
        return FIXED_TIME;
      }
    };
    Object.getOwnPropertyNames(OriginalDate).forEach((prop) => {
      if (prop in FixedDate) {
        return;
      }
      const descriptor = Object.getOwnPropertyDescriptor(OriginalDate, prop);
      if (descriptor) {
        Object.defineProperty(FixedDate, prop, descriptor);
      }
    });
    // eslint-disable-next-line no-global-assign
    Date = FixedDate;

    let seed = 1337;
    Math.random = () => {
      seed = (seed * 1664525 + 1013904223) % 4294967296;
      return seed / 4294967296;
    };

    const style = document.createElement('style');
    style.innerHTML = '*, *::before, *::after { transition: none !important; animation: none !important; }';
    document.head.appendChild(style);
  })();
`;

test.beforeEach(async ({ page }) => {
  await page.addInitScript(deterministicInitScript);
});

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
