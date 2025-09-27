import type { SvgIconComponent } from '@mui/icons-material';
import DashboardIcon from '@mui/icons-material/SpaceDashboardOutlined';
import TimelineIcon from '@mui/icons-material/InsightsOutlined';
import ScienceIcon from '@mui/icons-material/ScienceOutlined';
import CloudUploadIcon from '@mui/icons-material/CloudUploadOutlined';
import StackedLineChartIcon from '@mui/icons-material/StackedLineChartOutlined';
import SettingsIcon from '@mui/icons-material/SettingsOutlined';

export type AppRoute = {
  path: string;
  label: string;
  icon: SvgIconComponent;
};

export const appRoutes: AppRoute[] = [
  { path: '/', label: 'Live Dashboard', icon: DashboardIcon },
  { path: '/sessions', label: 'Session Evaluation', icon: TimelineIcon },
  { path: '/calibrations', label: 'Calibration Center', icon: ScienceIcon },
  { path: '/exports', label: 'Exports & Archives', icon: CloudUploadIcon },
  { path: '/service', label: 'Service Health', icon: StackedLineChartIcon },
  { path: '/settings', label: 'Settings', icon: SettingsIcon },
];
