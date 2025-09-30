import { Alert, AlertTitle, AlertDescription } from './ui/alert';
import { Info } from 'lucide-react';

export function CloseWarningBanner() {
  return (
    <Alert variant="info" className="rounded-none border-b">
      <Info className="h-4 w-4" />
      <AlertTitle>
        ⚠️ Keep This Tab Open
      </AlertTitle>
      <AlertDescription>
        Do not close this browser tab while capturing data. If closed accidentally, use the <strong>"Reopen Browser"</strong> button in the launcher.
      </AlertDescription>
    </Alert>
  );
}
