import React from 'react';
import { Alert, Card, CardContent, Chip, Divider, Stack, Typography } from '@mui/material';
import type { DiagnosticLogRowState, SeverityLevel } from './contracts';

const levelToColor = (level: SeverityLevel): 'default' | 'primary' | 'warning' | 'error' | 'success' => {
  switch (level) {
    case 'warning':
      return 'warning';
    case 'error':
      return 'error';
    case 'success':
      return 'success';
    case 'info':
    default:
      return 'primary';
  }
};

export interface LogFeedProps {
  title?: string;
  entries: DiagnosticLogRowState[];
  loading?: boolean;
  errorMessage?: string | null;
  emptyMessage?: string;
}

export const LogFeed: React.FC<LogFeedProps> = ({
  title = 'Live Alerts & Diagnostics',
  entries,
  loading = false,
  errorMessage = null,
  emptyMessage = 'No recent log events.',
}) => (
  <Card sx={{ minHeight: 320 }}>
    <CardContent>
      <Typography variant="h6" mb={2}>
        {title}
      </Typography>
      {errorMessage ? (
        <Alert severity="error" sx={{ mb: 2 }}>
          {errorMessage}
        </Alert>
      ) : null}
      <Stack spacing={2} divider={<Divider flexItem light />}>
        {loading && entries.length === 0 ? (
          <Stack alignItems="center" py={4} spacing={1}>
            <Typography variant="body2" color="text.secondary">
              Connecting to log stream…
            </Typography>
          </Stack>
        ) : entries.length === 0 ? (
          <Typography variant="body2" color="text.secondary">
            {emptyMessage}
          </Typography>
        ) : (
          entries.map((event) => (
            <Stack key={event.id} direction="row" spacing={1} alignItems="flex-start">
              <Chip size="small" label={event.level} color={levelToColor(event.level)} sx={{ textTransform: 'capitalize' }} />
              <Stack spacing={0.5}>
                <Typography variant="body2" fontWeight={600}>
                  {event.category}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {event.message}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {event.createdAtIso}
                </Typography>
              </Stack>
            </Stack>
          ))
        )}
      </Stack>
    </CardContent>
  </Card>
);

export default LogFeed;
