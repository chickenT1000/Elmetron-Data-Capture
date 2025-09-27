import { Navigate, Route, Routes } from 'react-router-dom';
import { AppLayout } from './layouts/AppLayout';
import DashboardPage from './pages/DashboardPage';
import SessionEvaluationPage from './pages/SessionEvaluationPage';
import CalibrationsPage from './pages/CalibrationsPage';
import ExportsPage from './pages/ExportsPage';
import ServiceHealthPage from './pages/ServiceHealthPage';
import SettingsPage from './pages/SettingsPage';

function App() {
  return (
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
  );
}

export default App;
