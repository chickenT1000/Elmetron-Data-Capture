import './App.css';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import DashboardPage from './pages/DashboardPage';
import SessionEvaluationPage from './pages/SessionEvaluationPage';
import CalibrationsPage from './pages/CalibrationsPage';
import ExportsPage from './pages/ExportsPage';
import ServiceHealthPage from './pages/ServiceHealthPage';
import SettingsPage from './pages/SettingsPage';
import { useConnectionMonitor } from './hooks/useConnectionMonitor';
import { OfflineWarning } from './components/OfflineWarning';
import { useState, useEffect } from 'react';

function App() {
  const connectionStatus = useConnectionMonitor();
  const [warningDismissed, setWarningDismissed] = useState(false);

  // Warn user before closing the tab
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      // Show warning when user tries to close the tab
      const message = 'Closing this tab will disconnect the dashboard from the capture service. You can reopen it from the launcher.';
      e.preventDefault();
      e.returnValue = message; // Standard for most browsers
      return message; // For older browsers
    };

    window.addEventListener('beforeunload', handleBeforeUnload);

    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  // Show warning when offline and not dismissed
  const showWarning = !connectionStatus.isOnline && !warningDismissed;

  const handleDismissWarning = () => {
    setWarningDismissed(true);
  };

  return (
    <>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="sessions" element={<SessionEvaluationPage />} />
          <Route path="calibrations" element={<CalibrationsPage />} />
          <Route path="exports" element={<ExportsPage />} />
          <Route path="service" element={<ServiceHealthPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>

      {/* Offline Warning Modal */}
      <OfflineWarning open={showWarning} onClose={handleDismissWarning} />
    </>
  );
}

export default App;
