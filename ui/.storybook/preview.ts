import type { Preview } from '@storybook/react-vite';

const applyDeterministicGlobals = () => {
  const globalScope = globalThis as typeof globalThis & {
    __deterministicPatched?: boolean;
    Date: DateConstructor;
  };

  if (typeof window === 'undefined' || globalScope.__deterministicPatched) {
    return;
  }

  const FIXED_TIME = Date.parse('2024-08-01T15:00:00Z');
  const OriginalDate = Date;

  const FixedDate = class extends OriginalDate {
    constructor(...args: ConstructorParameters<DateConstructor>) {
      if (args.length === 0) {
        super(FIXED_TIME);
      } else {
        super(...args);
      }
    }

    static now(): number {
      return FIXED_TIME;
    }
  } as unknown as DateConstructor;

  Object.getOwnPropertyNames(OriginalDate).forEach((prop) => {
    if ((FixedDate as unknown as Record<string, unknown>)[prop] !== undefined) {
      return;
    }
    const descriptor = Object.getOwnPropertyDescriptor(OriginalDate, prop as keyof DateConstructor);
    if (descriptor) {
      Object.defineProperty(FixedDate, prop, descriptor);
    }
  });

  globalScope.Date = FixedDate;

  let seed = 1337;
  Math.random = () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };

  if (typeof document !== 'undefined') {
    if (!document.head.querySelector('[data-deterministic-styles]')) {
      const style = document.createElement('style');
      style.setAttribute('data-deterministic-styles', 'true');
      style.innerHTML = `
        *, *::before, *::after {
          transition: none !important;
          animation: none !important;
          scroll-behavior: auto !important;
        }
      `;
      document.head.appendChild(style);
    }
  }

  globalScope.__deterministicPatched = true;
};

applyDeterministicGlobals();

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
       color: /(background|color)$/i,
       date: /Date$/i,
      },
    },
  },
};

export default preview;