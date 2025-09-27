import { Box, Button, Card, CardContent, Checkbox, FormControlLabel, Stack, Typography } from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import ArchiveIcon from '@mui/icons-material/Archive';

export default function ExportsPage() {
  return (
    <Stack spacing={3}>
      <Card>
        <CardContent>
          <Typography variant="h5" fontWeight={600} gutterBottom>
            Exports & Archives
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure export jobs, bundle archives, and review previous outputs.
          </Typography>
        </CardContent>
      </Card>
      <Box
        sx={{
          display: 'grid',
          gap: 3,
          gridTemplateColumns: { xs: '1fr', md: '320px 1fr' },
        }}
      >
        <Card sx={{ minHeight: 280 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Session Selection
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Choose sessions or overlays to export. Filters for latest runs, tags, and date ranges will be available here.
            </Typography>
          </CardContent>
        </Card>
        <Card sx={{ minHeight: 280 }}>
          <CardContent>
            <Typography variant="subtitle1" fontWeight={600} gutterBottom>
              Format & Archive Options
            </Typography>
            <Stack spacing={1.5}>
              {['CSV (compact)', 'JSON (full payload)', 'XML (LIMS)', 'PDF Summary', 'PNG Overlay Image'].map((label) => (
                <FormControlLabel key={label} control={<Checkbox defaultChecked />} label={label} />
              ))}
            </Stack>
            <Box mt={2} display="flex" gap={2}>
              <Button variant="outlined" startIcon={<ArchiveIcon />}>Bundle Archive</Button>
              <Button startIcon={<CloudUploadIcon />}>Launch Export Job</Button>
            </Box>
          </CardContent>
        </Card>
      </Box>
      <Card>
        <CardContent>
          <Typography variant="subtitle1" fontWeight={600} gutterBottom>
            Job History & Artefacts
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Recent exports with status, manifest checksum, archive summary, and download links will display here.
          </Typography>
        </CardContent>
      </Card>
    </Stack>
  );
}
