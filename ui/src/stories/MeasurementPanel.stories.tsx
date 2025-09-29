import type { Meta, StoryObj } from '@storybook/react';
import { ThemeProvider, CssBaseline, Container } from '@mui/material';
import theme from '../theme';
import { MeasurementPanel } from '../components/MeasurementPanel';
import type { MeasurementPanelState, MetricIndicatorState } from '../components/contracts';
import { toDeterministicIso } from './mocks/deterministic';

const meta: Meta<typeof MeasurementPanel> = {
  title: 'Dashboard/MeasurementPanel',
  component: MeasurementPanel,
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

type Story = StoryObj<typeof MeasurementPanel>;

const metricsSample: MetricIndicatorState[] = [
  {
    id: 'frames',
    label: 'Frames Processed',
    value: '154',
    helperText: 'Bytes read 15,338',
    iconToken: 'frames',
  },
  {
    id: 'queue',
    label: 'Command queue depth',
    value: '2',
    helperText: 'Inflight 1',
    iconToken: 'frames',
  },
  {
    id: 'processing',
    label: 'Avg processing time',
    value: '220.4 ms',
    helperText: 'Max 710.0 ms • throttled 3',
    iconToken: 'processing-time',
  },
  {
    id: 'latency',
    label: 'Health response latency',
    value: '85.3 ms',
    helperText: 'Last 72.0 ms • Max 141.2 ms',
    iconToken: 'latency',
  },
];

const readyState: MeasurementPanelState = {
  status: 'ready',
  autosaveEnabled: true,
  connection: 'connected',
  logStream: 'streaming',
  measurement: {
    value: 7.13,
    unit: 'pH',
    timestampIso: toDeterministicIso(),
    sequence: 1289,
    mode: 'Continuous',
    status: 'Stable',
    range: '0–14',
    temperature: {
      value: 21.8,
      unit: '°C',
    },
  },
};

export const Ready: Story = {
  args: {
    state: readyState,
    metrics: metricsSample,
  },
};

export const Offline: Story = {
  args: {
    state: {
      status: 'ready',
      autosaveEnabled: false,
      connection: 'offline',
      logStream: 'idle',
      measurement: {
        value: undefined,
        valueText: '—',
        unit: 'pH',
        timestampIso: toDeterministicIso(-5 * 60_000),
        sequence: 0,
        mode: 'Standby',
        status: 'Offline',
        range: '0–14',
        temperature: {
          value: null,
          unit: '°C',
        },
      },
    },
    metrics: metricsSample.map((metric) => ({
      ...metric,
      value: '—',
      helperText: undefined,
    })),
  },
};

export const Loading: Story = {
  args: {
    state: { status: 'loading' },
  },
};

export const Error: Story = {
  args: {
    state: { status: 'error', message: 'Instrument unreachable' },
  },
};

export const Empty: Story = {
  args: {
    state: { status: 'empty', message: 'Awaiting first capture window' },
  },
};
