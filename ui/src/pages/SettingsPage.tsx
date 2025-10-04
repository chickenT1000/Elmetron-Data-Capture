import { Card, CardContent, Stack, Typography, Switch, FormControlLabel, TextField, Button, Box, Slider, Alert } from '@mui/material';
import { useSettings, validateOperatorName } from '../contexts/SettingsContext';
import { useState, useEffect } from 'react';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';

export default function SettingsPage() {
  const { settings, updateSettings } = useSettings();
  const [localSettings, setLocalSettings] = useState(settings);
  const [hasChanges, setHasChanges] = useState(false);
  const [operatorNameError, setOperatorNameError] = useState<string | null>(null);

  // Update local settings when saved settings change
  useEffect(() => {
    setLocalSettings(settings);
    setHasChanges(false);
    setOperatorNameError(null);
  }, [settings]);

  // Track changes and validate
  useEffect(() => {
    const changed = JSON.stringify(localSettings) !== JSON.stringify(settings);
    setHasChanges(changed);
    
    // Validate operator name
    const error = validateOperatorName(localSettings.operatorName);
    setOperatorNameError(error);
  }, [localSettings, settings]);

  const handleSave = () => {
    // Final validation before saving
    const error = validateOperatorName(localSettings.operatorName);
    if (error) {
      setOperatorNameError(error);
      return;
    }
    updateSettings(localSettings);
  };

  const handleCancel = () => {
    setLocalSettings(settings);
    setOperatorNameError(null);
  };

  return (
    <Stack spacing={3}>
      {hasChanges && (
        <Alert severity={operatorNameError ? "error" : "warning"} sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <Box>
            {operatorNameError ? 'Fix validation errors before saving' : 'You have unsaved changes'}
          </Box>
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button 
              size="small" 
              variant="contained" 
              startIcon={<SaveIcon />} 
              onClick={handleSave}
              disabled={!!operatorNameError}
            >
              Save Changes
            </Button>
            <Button size="small" variant="outlined" startIcon={<CancelIcon />} onClick={handleCancel}>
              Cancel
            </Button>
          </Box>
        </Alert>
      )}

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
                  value={localSettings.gapThresholdSeconds}
                  onChange={(_, value) => setLocalSettings({ ...localSettings, gapThresholdSeconds: Math.min(60, Math.max(1, value as number)) })}
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
                  value={localSettings.gapThresholdSeconds}
                  onChange={(e) => setLocalSettings({ ...localSettings, gapThresholdSeconds: Math.min(60, Math.max(1, Number(e.target.value))) })}
                  inputProps={{ min: 1, max: 60, step: 1 }}
                  size="small"
                  sx={{ width: 100 }}
                  label="seconds"
                />
              </Box>
            </Box>

            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Auto-Scaling Y-Axis
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Automatically adjust chart Y-axis ranges using optimized preset scales. 
                Charts will select the smallest preset that fits your data with 10% buffer, 
                ensuring clean grid lines and stable visualization without erratic jumping.
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                <strong>When enabled:</strong> pH might show 6-8 range for neutral samples, 0-1000 µS/cm for drinking water, etc.
                <br />
                <strong>When disabled:</strong> Charts use fixed maximum ranges (pH: 0-14, Redox: ±2000 mV, Conductivity: 0-10,000 µS/cm, Temp: 0-50°C)
              </Typography>
              <FormControlLabel
                control={
                  <Switch
                    checked={localSettings.autoScalingEnabled}
                    onChange={(e) => setLocalSettings({ ...localSettings, autoScalingEnabled: e.target.checked })}
                  />
                }
                label={localSettings.autoScalingEnabled ? "Auto-scaling enabled (recommended)" : "Auto-scaling disabled (fixed ranges)"}
              />
            </Box>
          </Stack>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            General Settings
          </Typography>
          <Stack spacing={3}>
            <Box>
              <Typography variant="subtitle2" gutterBottom>
                Operator Name
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Set the default operator name that appears in the header and is associated with new sessions.
                This helps track who performed measurements and data collection.
              </Typography>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                Allowed: Letters, numbers, spaces, hyphens (-), underscores (_), and periods (.)
                <br />
                Maximum length: 50 characters
              </Typography>
              <TextField 
                label="Operator Name" 
                placeholder="Enter operator name" 
                size="small" 
                fullWidth
                value={localSettings.operatorName}
                onChange={(e) => setLocalSettings({ ...localSettings, operatorName: e.target.value })}
                error={!!operatorNameError}
                helperText={
                  operatorNameError 
                    ? operatorNameError 
                    : `${localSettings.operatorName.length}/50 characters - Click 'Save Changes' to apply`
                }
                inputProps={{ maxLength: 50 }}
              />
            </Box>
          </Stack>
        </CardContent>
      </Card>
    </Stack>
  );
}
