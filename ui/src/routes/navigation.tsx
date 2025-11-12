import type { SvgIconComponent } from '@mui/icons-material';
import DashboardIcon from '@mui/icons-material/SpaceDashboardOutlined';
import TimelineIcon from '@mui/icons-material/InsightsOutlined';
import ScienceIcon from '@mui/icons-material/ScienceOutlined';
import CloudUploadIcon from '@mui/icons-material/CloudUploadOutlined';
import StackedLineChartIcon from '@mui/icons-material/StackedLineChartOutlined';
import SettingsIcon from '@mui/icons-material/SettingsOutlined';

export type AppRoute = {
  path: string;
  labelKey: string; // Translation key instead of direct label
  icon: SvgIconComponent;
};

export const appRoutes: AppRoute[] = [
  { path: '/', labelKey: 'navigation.liveDashboard', icon: DashboardIcon },
  { path: '/sessions', labelKey: 'navigation.sessionEvaluation', icon: TimelineIcon },
  { path: '/calibrations', labelKey: 'navigation.calibrationCenter', icon: ScienceIcon },
  { path: '/exports', labelKey: 'navigation.exportsArchives', icon: CloudUploadIcon },
  { path: '/service', labelKey: 'navigation.serviceHealth', icon: StackedLineChartIcon },
  { path: '/settings', labelKey: 'navigation.settings', icon: SettingsIcon },
];
