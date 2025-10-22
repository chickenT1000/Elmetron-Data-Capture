import { Card, CardContent, Stack, Typography, Switch, FormControlLabel, TextField, Button } from '@mui/material';

export default function SettingsPage() {
  return (
    <Stack spacing={3}>
      <Card>
        <CardContent>
          <Typography variant="h5" fontWeight={600} gutterBottom>
            Application Settings
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Configure UI preferences, operator defaults, and data retention values.
          </Typography>
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <Stack spacing={2}>
            <FormControlLabel control={<Switch defaultChecked />} label="Enable dark mode automatically" />
            <TextField label="Default operator" placeholder="Operator name" size="small" />
            <TextField label="Data retention (days)" type="number" size="small" defaultValue={30} />
            <Button variant="contained" sx={{ alignSelf: 'flex-start' }}>
              Save Settings
            </Button>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
