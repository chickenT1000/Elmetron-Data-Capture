import './App.css';
import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import DashboardPage from './pages/DashboardPage';
const SessionEvaluationPage = lazy(() => import('./pages/SessionEvaluationPage'));
const CalibrationsPage = lazy(() => import('./pages/CalibrationsPage'));
const ExportsPage = lazy(() => import('./pages/ExportsPage'));
const ServiceHealthPage = lazy(() => import('./pages/ServiceHealthPage'));
const SettingsPage = lazy(() => import('./pages/SettingsPage'));
import { useConnectionMonitor } from './hooks/useConnectionMonitor';
import { OfflineWarning } from './components/OfflineWarning';
import { SettingsProvider } from './contexts/SettingsContext';
import { lazy, Suspense, useState } from 'react';
import { CircularProgress } from '@mui/material';


function App() {
  const connectionStatus = useConnectionMonitor();
  const [warningDismissed, setWarningDismissed] = useState(false);


  // Show warning when offline and not dismissed
  const showWarning = !connectionStatus.isOnline && !warningDismissed;

  const handleDismissWarning = () => {
    setWarningDismissed(true);
  };

  return (
    <SettingsProvider>
      <Suspense fallback={<CircularProgress aria-label="Loading" />}><Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="sessions" element={<SessionEvaluationPage />} />
          <Route path="calibrations" element={<CalibrationsPage />} />
          <Route path="exports" element={<ExportsPage />} />
          <Route path="service" element={<ServiceHealthPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes></Suspense>

      {/* Offline Warning Modal */}
      <OfflineWarning open={showWarning} onClose={handleDismissWarning} />
    </SettingsProvider>
  );
}

export default App;
