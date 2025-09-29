export type SeverityLevel = 'info' | 'success' | 'warning' | 'error';

export type ConnectionState = 'connected' | 'offline' | 'error';

export type LogStreamState = 'streaming' | 'polling' | 'idle';

export interface MeasurementSummary {
  value?: number | null;
  valueText?: string | null;
  unit?: string | null;
  temperature?: {
    value?: number | null;
    unit?: string | null;
  } | null;
  timestampIso?: string | null;
  capturedAtIso?: string | null;
  sequence?: number | string | null;
  mode?: string | null;
  status?: string | null;
  range?: string | null;
}

export type MeasurementPanelState =
  | {
      status: 'loading';
      message?: string;
    }
  | {
      status: 'empty';
      message?: string;
    }
  | {
      status: 'error';
      message: string;
    }
  | {
      status: 'ready';
      measurement: MeasurementSummary;
      connection: ConnectionState;
      autosaveEnabled: boolean;
      logStream: LogStreamState;
    };

export interface MetricIndicatorState {
  id: string;
  label: string;
  value: string;
  helperText?: string;
  tone?: SeverityLevel | 'default';
  iconToken?:
    | 'frames'
    | 'queue'
    | 'processing-time'
    | 'latency'
    | 'custom';
}

export interface CommandHistoryEntryState {
  timestampIso: string;
  queueDepth: number | null;
  inflight: number | null;
  backlog: number | null;
}

export interface DiagnosticLogRowState {
  id: string;
  level: SeverityLevel;
  category: string;
  message: string;
  createdAtIso: string;
  context?: Record<string, unknown>;
}

export interface DashboardContract {
  measurementPanel: MeasurementPanelState;
  metrics: MetricIndicatorState[];
  commandHistory: CommandHistoryEntryState[];
  logRows: DiagnosticLogRowState[];
}

export interface ComponentContracts {
  dashboard: DashboardContract;
}
