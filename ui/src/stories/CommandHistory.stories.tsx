import type { Meta, StoryObj } from '@storybook/react';
import { ThemeProvider, CssBaseline, Container } from '@mui/material';
import theme from '../theme';
import { CommandHistory } from '../components/CommandHistory';
import type { CommandHistoryEntryState } from '../components/contracts';
import { toDeterministicIso } from './mocks/deterministic';

const meta: Meta<typeof CommandHistory> = {
  title: 'Dashboard/CommandHistory',
  component: CommandHistory,
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

type Story = StoryObj<typeof CommandHistory>;

const entries: CommandHistoryEntryState[] = Array.from({ length: 6 }).map((_, index) => ({
  timestampIso: toDeterministicIso(-index * 60_000),
  queueDepth: Math.max(0, 3 - index),
  inflight: Math.max(0, 2 - index),
  backlog: index,
}));

export const Default: Story = {
  args: {
    entries,
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
    emptyMessage: 'No telemetry captured yet.',
  },
};
