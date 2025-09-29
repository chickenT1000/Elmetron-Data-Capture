import React from 'react';
import { Card, CardContent, Stack, Typography, Box } from '@mui/material';
import type { CommandHistoryEntryState } from './contracts';

export interface CommandHistoryProps {
  title?: string;
  entries: CommandHistoryEntryState[];
  loading?: boolean;
  emptyMessage?: string;
}

export const CommandHistory: React.FC<CommandHistoryProps> = ({
  title = 'Command Throughput (History)',
  entries,
  loading = false,
  emptyMessage = 'No command history available yet.',
}) => (
  <Card sx={{ minHeight: 240 }}>
    <CardContent>
      <Typography variant="h6" mb={2}>
        {title}
      </Typography>
      {entries.length === 0 ? (
        <Box
          sx={{
            borderRadius: 2,
            border: '1px dashed',
            borderColor: 'divider',
            height: 200,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'text.secondary',
          }}
        >
          {loading ? 'Loading telemetry…' : emptyMessage}
        </Box>
      ) : (
        <Box
          sx={{
            borderRadius: 2,
            border: '1px solid',
            borderColor: 'divider',
            height: 200,
            p: 2,
            overflow: 'auto',
            display: 'grid',
            gap: 1,
          }}
        >
          {entries.map((entry) => (
            <Stack key={entry.timestampIso} direction="row" spacing={2} alignItems="center">
              <Typography variant="body2" sx={{ minWidth: 180 }} color="text.secondary">
                {entry.timestampIso}
              </Typography>
              <Typography variant="body2">Queue {entry.queueDepth ?? '—'}</Typography>
              <Typography variant="body2">Inflight {entry.inflight ?? '—'}</Typography>
              <Typography variant="body2">Backlog {entry.backlog ?? '—'}</Typography>
            </Stack>
          ))}
        </Box>
      )}
    </CardContent>
  </Card>
);

export default CommandHistory;
