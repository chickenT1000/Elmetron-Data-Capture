import type { Meta, StoryObj } from '@storybook/react';
import { ThemeProvider, CssBaseline, Container } from '@mui/material';
import theme from '../theme';
import { LogFeed } from '../components/LogFeed';
import type { DiagnosticLogRowState } from '../components/contracts';

const meta: Meta<typeof LogFeed> = {
  title: 'Dashboard/LogFeed',
  component: LogFeed,
  parameters: {
    layout: 'fullscreen',
  },
  decorators: [
    (Story) => (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Container maxWidth="md" sx={{ py: 4 }}>
          <Story />
        </Container>
      </ThemeProvider>
    ),
  ],
};

export default meta;

type Story = StoryObj<typeof LogFeed>;

const logEntries: DiagnosticLogRowState[] = [
  {
    id: '1',
    level: 'info',
    category: 'capture',
    message: 'Capture window completed (512 bytes).',
    createdAtIso: new Date().toISOString(),
  },
  {
    id: '2',
    level: 'warning',
    category: 'command',
    message: 'Startup command LATENCY timed out after 3 attempts.',
    createdAtIso: new Date(Date.now() - 30_000).toISOString(),
  },
  {
    id: '3',
    level: 'error',
    category: 'watchdog',
    message: 'Watchdog detected stalled capture window.',
    createdAtIso: new Date(Date.now() - 90_000).toISOString(),
  },
];

export const WithEntries: Story = {
  args: {
    entries: logEntries,
  },
};

export const Loading: Story = {
  args: {
    entries: [],
    loading: true,
  },
};

export const Empty: Story = {
  args: {
    entries: [],
  },
};

export const ErrorState: Story = {
  args: {
    entries: [],
    errorMessage: 'Failed to load log stream',
  },
};
