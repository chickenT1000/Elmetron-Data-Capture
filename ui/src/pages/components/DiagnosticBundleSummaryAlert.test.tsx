import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import DiagnosticBundleSummaryAlert, { type BundleSummary } from './DiagnosticBundleSummaryAlert';

describe('DiagnosticBundleSummaryAlert', () => {
  it('renders summary details and handles dismiss', async () => {
    const summary: BundleSummary = {
      generatedLabel: '2025-09-27 10:15:00',
      eventsLabel: '3 log events',
      sessionsLabel: '2 session snapshots',
      databasePath: 'data/elmetron.sqlite',
      configAvailable: false,
    };
    const onClose = vi.fn();

    render(
      <DiagnosticBundleSummaryAlert summary={summary} filename="diagnostics.zip" onClose={onClose} />,
    );

    const alert = screen.getByTestId('diagnostic-bundle-summary');
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent(
      'Generated 2025-09-27 10:15:00 with 3 log events and 2 session snapshots.',
    );
    expect(screen.getByText('Saved as diagnostics.zip')).toBeInTheDocument();
    expect(screen.getByText('Database: data/elmetron.sqlite')).toBeInTheDocument();
    expect(screen.getByText('Configuration snapshot unavailable in this bundle.')).toBeInTheDocument();

    const user = userEvent.setup();
    await user.click(screen.getByLabelText(/close/i));
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
