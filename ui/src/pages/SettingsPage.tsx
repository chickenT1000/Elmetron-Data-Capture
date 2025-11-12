import { Card, CardContent, Stack, Typography, Switch, FormControlLabel, TextField, Button, Box, Slider, Alert, Autocomplete, Radio, RadioGroup, FormControl, FormLabel, Grid } from '@mui/material';
import { useSettings, validateOperatorName, type AutoscalingMode } from '../contexts/SettingsContext';
import { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchOperators, updateActiveSessionOperator, updateDefaultOperator } from '../api/sessions';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';

export default function SettingsPage() {
  const { settings, updateSettings } = useSettings();
  const queryClient = useQueryClient();
  const [localSettings, setLocalSettings] = useState(settings);
  const [hasChanges, setHasChanges] = useState(false);
  const [operatorNameError, setOperatorNameError] = useState<string | null>(null);
  
  // Fetch existing operator names
  const { data: operators = [] } = useQuery({
    queryKey: ['operators'],
    queryFn: fetchOperators,
    staleTime: 60000, // Cache for 1 minute
  });

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

  const handleSave = async () => {
    // Final validation before saving
    const error = validateOperatorName(localSettings.operatorName);
    if (error) {
      setOperatorNameError(error);
      return;
    }
    
    // Save settings to localStorage
    updateSettings(localSettings);
    
    // Update the default operator in backend config (for new sessions)
    try {
      await updateDefaultOperator(localSettings.operatorName);
    } catch (err) {
      console.error('Failed to update default operator config:', err);
      // Continue anyway - settings were saved to localStorage
    }
    
    // Update the active session's operator name (if exists)
    try {
      await updateActiveSessionOperator(localSettings.operatorName);
    } catch (err) {
      // Ignore 404 (no active session) - this is fine
      // Log other errors but don't block settings save
      if (err instanceof Error && !err.message.includes('404')) {
        console.warn('Failed to update active session operator:', err);
      }
    }
    
    // Invalidate operators cache to refetch after save
    // This ensures the dropdown shows the newly saved operator
    queryClient.invalidateQueries({ queryKey: ['operators'] });
  };

  const handleCancel = () => {
    setLocalSettings(settings);
    setOperatorNameError(null);
  };

  return (
    <Stack spacing={3} sx={{ position: 'relative' }}>
      {hasChanges && (
        <Alert 
          severity={operatorNameError ? "error" : "warning"} 
          sx={{ 
            position: 'fixed',
            top: 80,
            right: 24,
            zIndex: 1200,
            maxWidth: 500,
            boxShadow: 3,
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            animation: 'slideInRight 0.3s ease-out',
            '@keyframes slideInRight': {
              from: {
                transform: 'translateX(100%)',
                opacity: 0,
              },
              to: {
                transform: 'translateX(0)',
                opacity: 1,
              },
            },
          }}
        >
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
          <Typography variant="h6" gutterBottom>
            Operator Name
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Set the default operator name that appears in the header and is associated with new sessions.
            Select from existing operators or type a new name.
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ mb: 2, display: 'block' }}>
            Allowed: Letters, numbers, spaces, hyphens (-), underscores (_), and periods (.)
            <br />
            Maximum length: 50 characters
          </Typography>
          <Autocomplete
            freeSolo
            openOnFocus
            forcePopupIcon
            options={operators}
            value={localSettings.operatorName}
            onChange={(_, newValue) => {
              setLocalSettings({ ...localSettings, operatorName: newValue || '' });
            }}
            onInputChange={(_, newInputValue) => {
              setLocalSettings({ ...localSettings, operatorName: newInputValue });
            }}
            sx={{ maxWidth: 400 }}
            noOptionsText="No existing operators - type to add new"
            renderInput={(params) => (
              <TextField
                {...params}
                label="Operator Name"
                placeholder="Select existing or type new name"
                size="small"
                error={!!operatorNameError}
                helperText={
                  operatorNameError 
                    ? operatorNameError 
                    : operators.length > 0 
                      ? `${localSettings.operatorName.length}/50 characters - ${operators.length} existing operator(s) available. Click arrow to see list.`
                      : `${localSettings.operatorName.length}/50 characters - Click 'Save Changes' to apply`
                }
                inputProps={{ ...params.inputProps, maxLength: 50 }}
              />
            )}
            ListboxProps={{
              style: { maxHeight: '250px' }
            }}
          />
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Live Dashboard Settings
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Configure chart scaling and display options for the Live Dashboard.
          </Typography>
          
          <FormControl component="fieldset">
            <FormLabel component="legend" sx={{ mb: 1 }}>Charts Scaling Mode</FormLabel>
            <RadioGroup
              value={localSettings.autoscalingMode}
              onChange={(e) => setLocalSettings({ ...localSettings, autoscalingMode: e.target.value as AutoscalingMode })}
            >
              <FormControlLabel 
                value="presets" 
                control={<Radio />} 
                label="Autoscaling Presets (Recommended)" 
              />
              <Typography variant="caption" color="text.secondary" sx={{ ml: 4, mb: 1, display: 'block' }}>
                Charts automatically select from optimized preset ranges (e.g., pH: 0-14, 6-8, 4-10). Clean grid lines and stable visualization.
              </Typography>
              
              <FormControlLabel 
                value="dynamic" 
                control={<Radio />} 
                label="Dynamic Autoscaling" 
              />
              <Typography variant="caption" color="text.secondary" sx={{ ml: 4, mb: 1, display: 'block' }}>
                Charts fit data exactly with 10% buffer. More adaptive but may show unconventional ranges.
              </Typography>
              
              <FormControlLabel 
                value="fixed" 
                control={<Radio />} 
                label="Fixed Ranges (Custom)" 
              />
              <Typography variant="caption" color="text.secondary" sx={{ ml: 4, mb: 2, display: 'block' }}>
                Manually set exact min/max ranges for each parameter. Charts never change scale.
              </Typography>
            </RadioGroup>
          </FormControl>

          {localSettings.autoscalingMode === 'fixed' && localSettings.customRanges && (
            <Box sx={{ mt: 3, p: 2, bgcolor: 'background.default', borderRadius: 1 }}>
              <Typography variant="subtitle2" gutterBottom>
                Custom Range Settings
              </Typography>
              <Grid container spacing={2} sx={{ mt: 1 }}>
                <Grid item xs={12} sm={6}>
                  <Typography variant="caption" fontWeight={600} display="block" gutterBottom>
                    pH
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <TextField
                      label="Min"
                      type="number"
                      size="small"
                      value={localSettings.customRanges?.ph?.min ?? 0}
                      onChange={(e) => setLocalSettings({
                        ...localSettings,
                        customRanges: {
                          ...localSettings.customRanges,
                          ph: { ...(localSettings.customRanges?.ph || { min: 0, max: 14 }), min: Number(e.target.value) }
                        }
                      })}
                      inputProps={{ step: 0.1 }}
                    />
                    <Typography>–</Typography>
                    <TextField
                      label="Max"
                      type="number"
                      size="small"
                      value={localSettings.customRanges?.ph?.max ?? 14}
                      onChange={(e) => setLocalSettings({
                        ...localSettings,
                        customRanges: {
                          ...localSettings.customRanges,
                          ph: { ...(localSettings.customRanges?.ph || { min: 0, max: 14 }), max: Number(e.target.value) }
                        }
                      })}
                      inputProps={{ step: 0.1 }}
                    />
                  </Box>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <Typography variant="caption" fontWeight={600} display="block" gutterBottom>
                    Conductivity (µS/cm)
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <TextField
                      label="Min"
                      type="number"
                      size="small"
                      value={localSettings.customRanges?.conductivity?.min ?? 0}
                      onChange={(e) => setLocalSettings({
                        ...localSettings,
                        customRanges: {
                          ...localSettings.customRanges,
                          conductivity: { ...(localSettings.customRanges?.conductivity || { min: 0, max: 10000 }), min: Number(e.target.value) }
                        }
                      })}
                      inputProps={{ step: 10 }}
                    />
                    <Typography>–</Typography>
                    <TextField
                      label="Max"
                      type="number"
                      size="small"
                      value={localSettings.customRanges?.conductivity?.max ?? 10000}
                      onChange={(e) => setLocalSettings({
                        ...localSettings,
                        customRanges: {
                          ...localSettings.customRanges,
                          conductivity: { ...(localSettings.customRanges?.conductivity || { min: 0, max: 10000 }), max: Number(e.target.value) }
                        }
                      })}
                      inputProps={{ step: 10 }}
                    />
                  </Box>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <Typography variant="caption" fontWeight={600} display="block" gutterBottom>
                    Redox (mV)
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <TextField
                      label="Min"
                      type="number"
                      size="small"
                      value={localSettings.customRanges?.redox?.min ?? -2000}
                      onChange={(e) => setLocalSettings({
                        ...localSettings,
                        customRanges: {
                          ...localSettings.customRanges,
                          redox: { ...(localSettings.customRanges?.redox || { min: -2000, max: 2000 }), min: Number(e.target.value) }
                        }
                      })}
                      inputProps={{ step: 10 }}
                    />
                    <Typography>–</Typography>
                    <TextField
                      label="Max"
                      type="number"
                      size="small"
                      value={localSettings.customRanges?.redox?.max ?? 2000}
                      onChange={(e) => setLocalSettings({
                        ...localSettings,
                        customRanges: {
                          ...localSettings.customRanges,
                          redox: { ...(localSettings.customRanges?.redox || { min: -2000, max: 2000 }), max: Number(e.target.value) }
                        }
                      })}
                      inputProps={{ step: 10 }}
                    />
                  </Box>
                </Grid>

                <Grid item xs={12} sm={6}>
                  <Typography variant="caption" fontWeight={600} display="block" gutterBottom>
                    Temperature (°C)
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                    <TextField
                      label="Min"
                      type="number"
                      size="small"
                      value={localSettings.customRanges?.temperature?.min ?? 0}
                      onChange={(e) => setLocalSettings({
                        ...localSettings,
                        customRanges: {
                          ...localSettings.customRanges,
                          temperature: { ...(localSettings.customRanges?.temperature || { min: 0, max: 50 }), min: Number(e.target.value) }
                        }
                      })}
                      inputProps={{ step: 1 }}
                    />
                    <Typography>–</Typography>
                    <TextField
                      label="Max"
                      type="number"
                      size="small"
                      value={localSettings.customRanges?.temperature?.max ?? 50}
                      onChange={(e) => setLocalSettings({
                        ...localSettings,
                        customRanges: {
                          ...localSettings.customRanges,
                          temperature: { ...(localSettings.customRanges?.temperature || { min: 0, max: 50 }), max: Number(e.target.value) }
                        }
                      })}
                      inputProps={{ step: 1 }}
                    />
                  </Box>
                </Grid>
              </Grid>
            </Box>
          )}
          
          {/* Line Connection Threshold */}
          <Box sx={{ mt: 4 }}>
            <Typography variant="subtitle2" gutterBottom>
              Line Connection Threshold
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Maximum time gap in temperature data to draw continuous lines. Lines break when temperature has no data.
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              <strong>Recommended:</strong> 15 seconds (typical device polls every 2-5 seconds)
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, maxWidth: 400 }}>
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
                  { value: 45, label: '45s' },
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
                sx={{ width: 80 }}
                label="seconds"
              />
            </Box>
          </Box>
        </CardContent>
      </Card>

    </Stack>
  );
}
