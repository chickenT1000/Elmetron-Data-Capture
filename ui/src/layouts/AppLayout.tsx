import { useEffect, useState } from 'react';
import { Link, Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  AppBar,
  Toolbar,
  IconButton,
  Typography,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Box,
  CssBaseline,
  Divider,
  Tooltip,
  Select,
  MenuItem,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { appRoutes } from '../routes/navigation';
import { useLiveStatus } from '../hooks/useLiveStatus';
import { useHealthStatus } from '../hooks/useHealthStatus';
import { useHealthLogEvents } from '../hooks/useHealthLogEvents';
import { useSettings } from '../contexts/SettingsContext';
import { useTranslation } from 'react-i18next';

const drawerWidth = 240;

interface AppLayoutProps {
  onToggleTheme?: () => void;
  isDarkMode?: boolean;
}

export function AppLayout({ onToggleTheme, isDarkMode = false }: AppLayoutProps) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [recordingEnabled, setRecordingEnabled] = useState(true); // Simple on/off, default ON
  const location = useLocation();
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();

  const handleLanguageChange = (lang: string) => {
    i18n.changeLanguage(lang);
    localStorage.setItem('language', lang);
  };

  // Update document title based on current route
  useEffect(() => {
    const route = appRoutes.find(r => r.path === location.pathname);
    const pageTitle = route ? t(route.labelKey) : t('navigation.liveDashboard');
    document.title = `Elmetron - ${pageTitle}`;
  }, [location.pathname, t]);

  const { data: liveStatus, isError: liveStatusError } = useLiveStatus();
  const { data: health } = useHealthStatus(3000);
  const { connectionState: logConnectionState } = useHealthLogEvents({ limit: 5, fallbackMs: 5000 });
  const { settings } = useSettings();

  const handleDrawerToggle = () => {
    setMobileOpen((prev) => !prev);
  };

  const handleRecordingToggle = () => {
    setRecordingEnabled((prev) => !prev);
  };

  // Determine if backend is completely down
  const backendDown = liveStatusError || !health;
  
  // Determine mode
  const mode = backendDown ? 'offline' : (liveStatus?.mode ?? 'archive');
  const isLiveMode = mode === 'live';
  const isOffline = mode === 'offline';
  
  // Mode indicator color
  const modeColor = isOffline ? 'error' : (isLiveMode ? 'success' : 'warning');
  const modeLabel = isOffline ? t('header.mode.offline') : (isLiveMode ? t('header.mode.live') : t('header.mode.archive'));
  const modeTooltip = isOffline 
    ? t('header.modeTooltip.offline')
    : (isLiveMode 
      ? t('header.modeTooltip.live')
      : t('header.modeTooltip.archive'));

  // Device info - only show device in Live mode
  const deviceLabel = isLiveMode && liveStatus?.instrument
    ? `${liveStatus.instrument.model} · ${liveStatus.instrument.serial}`
    : t('header.device.noDevice');
  
  const deviceConnected = isLiveMode && (liveStatus?.device_connected ?? false);
  const deviceColor = deviceConnected ? 'success' : 'default';

  // Service Health Aggregation
  // Comprehensive health check combining multiple indicators
  const getServiceHealth = (): { status: 'error' | 'warning' | 'success'; tooltip: string } => {
    // CRITICAL (RED DOT) - Backend is completely down
    if (backendDown) {
      return { status: 'error', tooltip: t('header.serviceHealthTooltip.critical', { message: t('healthMessages.backendOffline') }) };
    }
    
    // CRITICAL (RED DOT) - Service is broken or critical failure
    if (health?.watchdog_alert) {
      return { status: 'error', tooltip: t('header.serviceHealthTooltip.critical', { message: t('healthMessages.watchdogAlert') }) };
    }

    // WARNING (YELLOW DOT) - Service is running but has issues
    const warnings: string[] = [];
    
    // 1. Capture service not running
    if (health.state !== 'running') {
      warnings.push(t('healthMessages.captureNotRunning'));
    }
    
    // 2. Log connection issues in Live Mode
    if (isLiveMode && logConnectionState === 'error') {
      warnings.push(t('healthMessages.logConnectionFailed'));
    }
    
    // 3. No device connected in Live Mode (should be connected)
    if (isLiveMode && !deviceConnected) {
      warnings.push(t('healthMessages.deviceNotConnected'));
    }
    
    // 4. Log stream idle in Live Mode (expected to be streaming/polling)
    if (isLiveMode && logConnectionState !== 'streaming' && logConnectionState !== 'polling') {
      warnings.push(t('healthMessages.logStreamIdle'));
    }

    // If we have warnings, return yellow dot
    if (warnings.length > 0) {
      return { 
        status: 'warning', 
        tooltip: t('header.serviceHealthTooltip.warning', { message: warnings.join(', ') })
      };
    }

    // HEALTHY (GREEN DOT) - Everything is working
    return { 
      status: 'success', 
      tooltip: t('header.serviceHealthTooltip.healthy')
    };
  };

  const serviceHealth = getServiceHealth();
  const healthStatus = serviceHealth.status;
  const healthTooltip = serviceHealth.tooltip;

  const drawer = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box
        component={Link}
        to="/"
        sx={{
          px: 2,
          py: 3,
          textDecoration: 'none',
          color: 'inherit',
          cursor: 'pointer',
          '&:hover': {
            backgroundColor: 'action.hover',
          },
        }}
      >
        <Typography variant="h6" fontWeight={700} color="primary">
          {t('app.title')}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {t('app.subtitle')}
        </Typography>
      </Box>
      <Divider />
      <List sx={{ flexGrow: 1 }}>
        {appRoutes.map((route) => {
          const isActive = location.pathname === route.path;
          return (
            <ListItemButton
              key={route.path}
              selected={isActive}
              onClick={() => {
                navigate(route.path);
                setMobileOpen(false);
              }}
            >
              <ListItemIcon>
                <route.icon color={isActive ? 'primary' : 'inherit'} />
              </ListItemIcon>
              <ListItemText primary={t(route.labelKey)} />
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <CssBaseline />
      <AppBar
        position="fixed"
        sx={{
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          ml: { sm: `${drawerWidth}px` },
          boxShadow: '0 4px 12px rgba(10, 61, 98, 0.1)',
          backdropFilter: 'blur(6px)',
        }}
        color="inherit"
      >
        <Toolbar sx={{ display: 'flex', justifyContent: 'space-between', gap: 3, flexWrap: 'wrap', py: 1 }}>
          {/* LEFT: Mobile menu + Mode */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 0, display: { sm: 'none' } }}
            >
              <MenuIcon />
            </IconButton>
            
            {/* Mode Indicator */}
            <Tooltip title={modeTooltip}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <FiberManualRecordIcon 
                  color={modeColor} 
                  sx={{ fontSize: 12 }} 
                />
                <Typography variant="body2" color="text.secondary">
                  {modeLabel}
                </Typography>
              </Box>
            </Tooltip>
          </Box>
          
          {/* Device Status */}
          <Tooltip title={deviceConnected ? t('header.device.connected', { deviceLabel }) : t('header.device.notConnected')}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FiberManualRecordIcon color={deviceColor} sx={{ fontSize: 12 }} />
              <Typography variant="body2" color="text.secondary">
                {deviceLabel}
              </Typography>
            </Box>
          </Tooltip>

          {/* CENTER: Service Health */}
          <Tooltip title={healthTooltip}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FiberManualRecordIcon 
                color={healthStatus} 
                sx={{ fontSize: 12 }} 
              />
              <Typography variant="body2" color="text.secondary">
                {t('header.serviceHealth')}
              </Typography>
            </Box>
          </Tooltip>

          {/* Recording Indicator */}
          <Tooltip title={backendDown ? t('header.recordingTooltip.offline') : (recordingEnabled ? t('header.recordingTooltip.on') : t('header.recordingTooltip.off'))}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FiberManualRecordIcon 
                color={backendDown ? 'default' : (recordingEnabled ? 'success' : 'default')} 
                sx={{ fontSize: 12 }} 
              />
              <Typography variant="body2" color="text.secondary">
                {t('header.recording')}
              </Typography>
            </Box>
          </Tooltip>

          {/* RIGHT: Operator + Language Selector + Theme Toggle */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Tooltip title={t('header.operatorTooltip')}>
              <Typography variant="body2" color="text.secondary">
                {t('header.operator')} <Box component="span" color="text.primary">{settings.operatorName}</Box>
              </Typography>
            </Tooltip>
            
            {/* Language Selector */}
            <Tooltip title={t('header.language.tooltip')}>
              <Select
                value={i18n.language}
                onChange={(e) => handleLanguageChange(e.target.value)}
                size="small"
                sx={{ 
                  minWidth: 60,
                  height: 32,
                  '& .MuiSelect-select': {
                    py: 0.5,
                    px: 1,
                  }
                }}
              >
                <MenuItem value="en">EN</MenuItem>
                <MenuItem value="pl">PL</MenuItem>
              </Select>
            </Tooltip>
            
            {onToggleTheme && (
              <Tooltip title={isDarkMode ? t('header.theme.switchToLight') : t('header.theme.switchToDark')}>
                <IconButton onClick={onToggleTheme} color="primary" size="small">
                  {isDarkMode ? <Brightness7Icon /> : <Brightness4Icon />}
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Toolbar>
      </AppBar>
      <Box
        component="nav"
        sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
        aria-label="main navigation"
      >
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={handleDrawerToggle}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: 'block', sm: 'none' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
        >
          {drawer}
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: 'none', sm: 'block' },
            '& .MuiDrawer-paper': { boxSizing: 'border-box', width: drawerWidth },
          }}
          open
        >
          {drawer}
        </Drawer>
      </Box>
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          px: 3,
          pb: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
          backgroundColor: 'background.default',
        }}
      >
        <Outlet context={{ recordingEnabled, onRecordingToggle: handleRecordingToggle }} />
      </Box>
    </Box>
  );
}
