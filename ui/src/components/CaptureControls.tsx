import { useState } from 'react';
import { Alert, Button, Card, CardContent, Stack, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useLiveStatus } from '../hooks/useLiveStatus';
import { buildApiUrl } from '../config';
import { requestJson } from '../api/client';

export default function CaptureControls() {
  const { i18n } = useTranslation();
  const pl = i18n.language.startsWith('pl');
  const { data, refetch } = useLiveStatus();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const active = ['running', 'starting', 'reconnecting', 'stale'].includes(data?.state || '');
  async function selectArchive(mode: string) {
    setBusy(true);setError('');
    try { await requestJson(buildApiUrl('/api/archive/select'), {method:'POST', headers:{'Content-Type':'application/json'},body:JSON.stringify({mode})}); await refetch(); window.location.reload(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  async function shutdown() {
    setBusy(true);setError('');
    try { await requestJson(buildApiUrl('/api/server/shutdown'), {method:'POST'}); setError(pl ? 'Usługa została zamknięta. Możesz zamknąć kartę.' : 'Service closed. You can close this tab.'); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  async function action(operation: string, demo = false) {
    setBusy(true); setError('');
    try { await requestJson(buildApiUrl(`/api/capture/${operation}`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ demo }) }); await refetch(); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  return <Card><CardContent><Stack spacing={2}>
    <Typography variant="h6">{pl ? 'Rejestracja pomiarów' : 'Capture measurements'}</Typography>
    {data?.mode === 'demo' && <Alert severity="info">{pl ? 'DEMO — dane syntetyczne w osobnej bazie.' : 'DEMO — synthetic data in a separate database.'}</Alert>}
    <Typography variant="body2">{pl ? 'Zamknięcie karty nie zatrzymuje rejestracji. Użyj przycisku Zatrzymaj.' : 'Closing this tab does not stop capture. Use Stop.'}</Typography>
    <Stack direction="row" spacing={2} flexWrap="wrap">
      <Button disabled={busy || active} onClick={() => action('start')}>{pl ? 'Uruchom CX-505' : 'Start CX-505'}</Button>
      <Button disabled={busy || active} variant="outlined" onClick={() => action('start', true)}>{pl ? 'Uruchom demonstrację' : 'Start demo'}</Button>
      <Button disabled={busy || !active} color="error" variant="outlined" onClick={() => action('stop')}>{pl ? 'Zatrzymaj' : 'Stop'}</Button>
    </Stack>
    <Stack direction="row" spacing={2}>
      <Button disabled={busy || active} onClick={()=>selectArchive('archive')}>{pl ? 'Archiwum pomiarów' : 'Measurement archive'}</Button>
      <Button disabled={busy || active} onClick={()=>selectArchive('demo')}>{pl ? 'Archiwum demo' : 'Demo archive'}</Button>
      <Button disabled={busy} onClick={shutdown}>{pl ? 'Zamknij usługę' : 'Close service'}</Button>
    </Stack>
    {(error || data?.detail) && <Alert severity="warning">{error || data?.detail}</Alert>}
  </Stack></CardContent></Card>;
}
