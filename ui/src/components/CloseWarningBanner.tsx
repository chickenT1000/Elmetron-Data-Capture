import { Alert, AlertTitle } from '@mui/material';
import InfoIcon from '@mui/icons-material/Info';

export function CloseWarningBanner() {
  return (
    <Alert 
      severity="info" 
      icon={<InfoIcon />}
      sx={{
        borderRadius: 0,
        borderBottom: '1px solid',
        borderColor: 'info.main',
        '& .MuiAlert-message': {
          width: '100%'
        }
      }}
    >
      <AlertTitle sx={{ fontWeight: 600, mb: 0.5 }}>
        ⚠️ Keep This Tab Open
      </AlertTitle>
      Do not close this browser tab while capturing data. If closed accidentally, use the <strong>"Reopen Browser"</strong> button in the launcher.
    </Alert>
  );
}
