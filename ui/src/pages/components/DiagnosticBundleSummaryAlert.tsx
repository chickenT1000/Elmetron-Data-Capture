import { Alert, AlertTitle, Typography } from '@mui/material';

export interface BundleSummary {
  generatedLabel: string;
  eventsLabel: string;
  sessionsLabel: string;
  databasePath: string | null;
  configAvailable: boolean | null;
}

export interface DiagnosticBundleSummaryAlertProps {
  summary: BundleSummary;
  filename: string | null;
  onClose: () => void;
}

export default function DiagnosticBundleSummaryAlert({
  summary,
  filename,
  onClose,
}: DiagnosticBundleSummaryAlertProps) {
  return (
    <Alert
      severity="success"
      sx={{ mt: 2 }}
      onClose={onClose}
      data-testid="diagnostic-bundle-summary"
    >
      <AlertTitle>Diagnostic bundle ready</AlertTitle>
      <Typography variant="body2">
        {`Generated ${summary.generatedLabel} with ${summary.eventsLabel} and ${summary.sessionsLabel}.`}
      </Typography>
      {filename ? (
        <Typography variant="caption" sx={{ mt: 1 }} display="block">
          Saved as {filename}
        </Typography>
      ) : null}
      {summary.databasePath ? (
        <Typography
          variant="caption"
          sx={{ mt: 0.5 }}
          display="block"
          color="text.secondary"
        >
          Database: {summary.databasePath}
        </Typography>
      ) : null}
      {summary.configAvailable === false ? (
        <Typography
          variant="caption"
          sx={{ mt: 0.5 }}
          display="block"
          color="text.secondary"
        >
          Configuration snapshot unavailable in this bundle.
        </Typography>
      ) : null}
    </Alert>
  );
}
