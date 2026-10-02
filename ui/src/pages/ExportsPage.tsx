import { useState } from 'react';
import { Alert, Button, Card, CardContent, MenuItem, Select, Stack, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useRecentSessions } from '../hooks/useRecentSessions';
import { buildApiUrl } from '../config';

export default function ExportsPage() {
  const { i18n } = useTranslation(); const pl = i18n.language.startsWith('pl');
  const { data: sessions = [] } = useRecentSessions(1000);
  const [session, setSession] = useState<number | ''>(''); const [format, setFormat] = useState('csv');
  const [busy, setBusy] = useState(false); const [error, setError] = useState('');
  async function download() {
    setBusy(true); setError('');
    try {
      const response = await fetch(buildApiUrl(`/api/sessions/${session}/export?format=${format}`));
      if (!response.ok) throw new Error((await response.json()).error);
      const url = URL.createObjectURL(await response.blob()); const link = document.createElement('a');
      link.href = url; link.download = `session_${session}.${format}`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    } catch (e) { setError(e instanceof Error ? e.message : String(e)); }
    finally { setBusy(false); }
  }
  return <Card><CardContent><Stack spacing={3}>
    <Typography variant="h5">{pl ? 'Eksport pomiarów' : 'Export measurements'}</Typography>
    <Typography>{pl ? 'Eksport obejmuje wszystkie pomiary sesji, również punkty pominięte przy wyświetlaniu dużego wykresu. Obraz wykresu pobierzesz w zakładce Sesje.' : 'Exports include all session measurements, including points sampled out of large charts. Download chart images from Sessions.'}</Typography>
    {!sessions.length && <Alert severity="info">{pl ? 'Archiwum jest puste. Uruchom rejestrację lub demonstrację.' : 'No sessions. Start capture or demonstration.'}</Alert>}
    <Select value={session} displayEmpty onChange={e => setSession(Number(e.target.value))} inputProps={{ 'aria-label': pl ? 'Sesja' : 'Session' }}>
      <MenuItem value="" disabled>{pl ? 'Wybierz sesję' : 'Select session'}</MenuItem>
      {sessions.map(s => <MenuItem key={s.id} value={s.id}>{s.note || `#${s.id}`} — {s.started_at}</MenuItem>)}
    </Select>
    <Select value={format} onChange={e => setFormat(e.target.value)} inputProps={{ 'aria-label': pl ? 'Format' : 'Format' }}>
      {['csv', 'json', 'xml', 'pdf', 'zip'].map(f => <MenuItem key={f} value={f}>{f.toUpperCase()}</MenuItem>)}
    </Select>
    <Button disabled={busy || !session} onClick={download}>{pl ? 'Pobierz eksport' : 'Download export'}</Button>
    {error && <Alert severity="error">{error}</Alert>}
  </Stack></CardContent></Card>;
}
