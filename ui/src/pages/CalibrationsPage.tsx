import { useEffect, useState } from 'react';
import { Alert, Button, Card, CardContent, MenuItem, Select, Stack, TextField, Typography } from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useRecentSessions } from '../hooks/useRecentSessions';
import { buildApiUrl } from '../config';
import { requestJson } from '../api/client';
interface Calibration { id: number; author: string; label: string; note: string; performed_at: string; }
export default function CalibrationsPage() {
  const { i18n } = useTranslation(); const pl = i18n.language.startsWith('pl');
  const { data: sessions = [] } = useRecentSessions(1000);
  const [session, setSession] = useState<number | ''>(''); const [label, setLabel] = useState('');
  const [author, setAuthor] = useState(''); const [note, setNote] = useState('');
  const [rows, setRows] = useState<Calibration[]>([]); const [error, setError] = useState(''); const [busy, setBusy] = useState(false);
  async function refresh(id: number) { const result = await requestJson<{ calibrations: Calibration[] }>(buildApiUrl(`/api/sessions/${id}/calibrations`)); setRows(result.calibrations); }
  useEffect(() => { if (session) refresh(session).catch(e => setError(String(e))); else setRows([]); }, [session]);
  async function save() {
    setBusy(true); setError('');
    try { await requestJson(buildApiUrl(`/api/sessions/${session}/calibrations`), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ label, author, note }) }); await refresh(Number(session)); setNote(''); }
    catch (e) { setError(e instanceof Error ? e.message : String(e)); } finally { setBusy(false); }
  }
  return <Card><CardContent><Stack spacing={2}>
    <Typography variant="h5">{pl ? 'Rejestr kalibracji' : 'Calibration records'}</Typography>
    <Alert severity="info">{pl ? 'Kalibrację wykonaj na mierniku. Ten formularz zapisuje jej opis i autora.' : 'Perform calibration on the instrument. This form records its description and operator.'}</Alert>
    <Select value={session} displayEmpty onChange={e => setSession(Number(e.target.value))} inputProps={{ 'aria-label': pl ? 'Sesja' : 'Session' }}>
      <MenuItem value="" disabled>{pl ? 'Wybierz sesję' : 'Select session'}</MenuItem>
      {sessions.map(s => <MenuItem key={s.id} value={s.id}>{s.note || `#${s.id}`}</MenuItem>)}
    </Select>
    <TextField label={pl ? 'Wzorzec / opis' : 'Reference / label'} value={label} onChange={e => setLabel(e.target.value)} inputProps={{ maxLength: 100 }} />
    <TextField label={pl ? 'Operator' : 'Operator'} value={author} onChange={e => setAuthor(e.target.value)} inputProps={{ maxLength: 100 }} />
    <TextField label={pl ? 'Notatka' : 'Note'} value={note} onChange={e => setNote(e.target.value)} multiline inputProps={{ maxLength: 1000 }} />
    <Button disabled={!session || !label.trim() || !author.trim() || busy} onClick={save}>{pl ? 'Zapisz kalibrację' : 'Record calibration'}</Button>
    {error && <Alert severity="error">{error}</Alert>}
    {rows.map(r => <Alert key={r.id} severity="success">{r.performed_at} · {r.author} · {r.label} — {r.note}</Alert>)}
  </Stack></CardContent></Card>;
}
