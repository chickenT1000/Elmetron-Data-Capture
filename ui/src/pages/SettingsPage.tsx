import { Card, CardContent, Stack, Typography, Switch, FormControlLabel, TextField, Button, Box, Slider } from '@mui/material';
import { useChartSettings } from '../hooks/useChartSettings';

export default function SettingsPage() {
  const { settings, updateGapThreshold } = useChartSettings();

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
          <Typography variant="h6" gutterBottom>
            Chart Display Settings
          </Typography>
          <Stack spacing={3}>
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Line Connection Threshold
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Maximum time gap in temperature data (reference channel) to draw continuous lines on rolling charts. 
                Since temperature streams continuously with all measurements, gaps in temperature indicate device disconnection.
                Lines break only when temperature has no data, preventing misleading connections across true interruptions.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                <strong>How it works:</strong> If pH has a 20s gap but temperature still has data, pH line stays connected (just timing variation).
                Lines only break when temperature also has no data = true device disconnection.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                <strong>Recommended:</strong> 15 seconds (typical device polls every 2-5 seconds)
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Slider
                  value={settings.gapThresholdSeconds}
                  onChange={(_, value) => updateGapThreshold(value as number)}
                  min={1}
                  max={60}
                  step={1}
                  marks={[
                    { value: 1, label: '1s' },
                    { value: 15, label: '15s' },
                    { value: 30, label: '30s' },
                    { value: 60, label: '60s' },
                  ]}
                  valueLabelDisplay="auto"
                  valueLabelFormat={(value) => `${value}s`}
                  sx={{ flex: 1 }}
                />
                <TextField
                  type="number"
                  value={settings.gapThresholdSeconds}
                  onChange={(e) => updateGapThreshold(Number(e.target.value))}
                  inputProps={{ min: 1, max: 60, step: 1 }}
                  size="small"
                  sx={{ width: 100 }}
                  label="seconds"
                />
              </Box>
            </Box>
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            General Settings
          </Typography>
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
