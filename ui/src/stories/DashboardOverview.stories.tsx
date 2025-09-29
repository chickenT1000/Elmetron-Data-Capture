import type { Meta, StoryObj } from '@storybook/react';
import { ThemeProvider, CssBaseline, Container, Stack } from '@mui/material';
import theme from '../theme';
import { MeasurementPanel } from '../components/MeasurementPanel';
import { CommandHistory } from '../components/CommandHistory';
import { LogFeed } from '../components/LogFeed';
import type {
  MeasurementPanelState,
  MetricIndicatorState,
  CommandHistoryEntryState,
  DiagnosticLogRowState,
} from '../components/contracts';
import { toDeterministicIso } from './mocks/deterministic';

const meta: Meta = {
  title: 'Dashboard/Overview',
  parameters: {
    layout: 'fullscreen',
  },
  decorators: [
    (Story) => (
      <ThemeProvider theme={theme}>
        <CssBaseline />
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <Story />
        </Container>
      </ThemeProvider>
    ),
  ],
};

export default meta;

type Story = StoryObj;

const measurementState: MeasurementPanelState = {
  status: 'ready',
  autosaveEnabled: true,
  connection: 'connected',
  logStream: 'streaming',
  measurement: {
    value: 7.08,
    unit: 'pH',
    timestampIso: toDeterministicIso(),
    sequence: 1942,
    mode: 'Continuous',
    status: 'Stable',
    range: '0–14',
    temperature: {
      value: 22.4,
      unit: '°C',
    },
  },
};

const metrics: MetricIndicatorState[] = [
  {
    id: 'frames',
    label: 'Frames Processed',
    value: '268',
    helperText: 'Bytes read 27,612',
    iconToken: 'frames',
  },
  {
    id: 'queue',
    label: 'Command queue depth',
    value: '1',
    helperText: 'Inflight 0',
    iconToken: 'frames',
  },
  {
    id: 'processing',
    label: 'Avg processing time',
    value: '198.5 ms',
    helperText: 'Max 640.0 ms • throttled 2',
    iconToken: 'processing-time',
  },
  {
    id: 'latency',
    label: 'Health response latency',
    value: '92.3 ms',
    helperText: 'Last 78.0 ms • Max 150.2 ms',
    iconToken: 'latency',
  },
];

const commandHistoryEntries: CommandHistoryEntryState[] = Array.from({ length: 6 }).map((_, index) => ({
  timestampIso: toDeterministicIso(-index * 90_000),
  queueDepth: Math.max(0, 2 - index),
  inflight: Math.max(0, 1 - index),
  backlog: index,
}));

const logEntries: DiagnosticLogRowState[] = [
  {
    id: 'log-1',
    level: 'info',
    category: 'capture',
    message: 'Capture window completed (768 bytes).',
    createdAtIso: toDeterministicIso(),
  },
  {
    id: 'log-2',
    level: 'warning',
    category: 'command',
    message: 'Startup command CALIBRATE took longer than expected.',
    createdAtIso: toDeterministicIso(-45_000),
  },
  {
    id: 'log-3',
    level: 'error',
    category: 'watchdog',
    message: 'Watchdog issued reconnect attempt (attempt 2).',
    createdAtIso: toDeterministicIso(-120_000),
  },
];

export const Default: Story = {
  render: () => (
    <Stack spacing={3}>
      <MeasurementPanel state={measurementState} metrics={metrics} />
      <CommandHistory entries={commandHistoryEntries} />
      <LogFeed entries={logEntries} />
    </Stack>
  ),
};

export const Errors: Story = {
  render: () => (
    <Stack spacing={3}>
      <MeasurementPanel
        state={{
          status: 'ready',
          autosaveEnabled: false,
          connection: 'error',
          logStream: 'polling',
          measurement: {
            value: undefined,
            valueText: null,
            unit: 'pH',
            timestampIso: toDeterministicIso(-10 * 60_000),
            mode: 'Unknown',
            status: 'Error',
            range: '0–14',
            temperature: {
              value: null,
              unit: '°C',
            },
          },
        }}
        metrics={metrics.map((metric) => ({ ...metric, value: '—', helperText: undefined }))}
      />
      <CommandHistory
        entries={commandHistoryEntries.map((entry) => ({
          ...entry,
          queueDepth: entry.queueDepth ? entry.queueDepth + 4 : 4,
          inflight: entry.inflight ? entry.inflight + 2 : 2,
          backlog: entry.backlog + 5,
        }))}
      />
      <LogFeed
        entries={[
          {
            id: 'err-1',
            level: 'error',
            category: 'capture',
            message: 'Capture window failed: FT_STATUS_DEVICE_NOT_FOUND',
            createdAtIso: toDeterministicIso(),
          },
          {
            id: 'warn-1',
            level: 'warning',
            category: 'command',
            message: 'Command queue backlog exceeded expected threshold (8)',
            createdAtIso: toDeterministicIso(-30_000),
          },
          {
            id: 'info-1',
            level: 'info',
            category: 'watchdog',
            message: 'Attempting interface reopen (1/5)',
            createdAtIso: toDeterministicIso(-60_000),
          },
        ]}
        errorMessage="Health stream degraded"
      />
    </Stack>
  ),
};
