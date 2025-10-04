import { useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
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
  Switch,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import FiberManualRecordIcon from '@mui/icons-material/FiberManualRecord';
import Brightness4Icon from '@mui/icons-material/Brightness4';
import Brightness7Icon from '@mui/icons-material/Brightness7';
import { appRoutes } from '../routes/navigation';
import { useLiveStatus } from '../hooks/useLiveStatus';
import { useHealthStatus } from '../hooks/useHealthStatus';
import { useSettings } from '../contexts/SettingsContext';

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

  const { data: liveStatus } = useLiveStatus();
  const { data: health } = useHealthStatus(3000);
  const { settings } = useSettings();

  const handleDrawerToggle = () => {
    setMobileOpen((prev) => !prev);
  };

  const handleRecordingToggle = () => {
    setRecordingEnabled((prev) => !prev);
  };

  // Determine mode
  const mode = liveStatus?.mode ?? 'archive';
  const isLiveMode = mode === 'live';
  const modeColor = isLiveMode ? 'success' : 'info';

  // Device info
  const deviceLabel = liveStatus?.instrument
    ? `${liveStatus.instrument.model} · ${liveStatus.instrument.serial}`
    : 'No Device Connected';
  
  const deviceConnected = liveStatus?.device_connected ?? false;
  const deviceColor = deviceConnected ? 'success' : 'default';

  // Health status (aggregate)
  const healthStatus = health?.watchdog_alert
    ? 'error'
    : health?.state === 'running'
    ? 'success'
    : 'warning';

  const drawer = (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <Box sx={{ px: 2, py: 3 }}>
        <Typography variant="h6" fontWeight={700} color="primary">
          Elmetron
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Monitoring Suite
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
              <ListItemText primary={route.label} />
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
            <Tooltip title={isLiveMode ? "Device is connected and streaming data" : "No device connected, viewing historical data"}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <FiberManualRecordIcon 
                  color={modeColor} 
                  sx={{ fontSize: 12 }} 
                />
                <Typography variant="body2" color="text.secondary">
                  {isLiveMode ? 'Live Mode' : 'Archive Mode'}
                </Typography>
              </Box>
            </Tooltip>
          </Box>
          
          {/* Device Status */}
          <Tooltip title={deviceConnected ? `Device connected: ${deviceLabel}` : "No device connected"}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              {deviceConnected && (
                <FiberManualRecordIcon color={deviceColor} sx={{ fontSize: 12 }} />
              )}
              <Typography variant="body2" color="text.secondary">
                {deviceLabel}
              </Typography>
            </Box>
          </Tooltip>

          {/* CENTER: Service Health */}
          <Tooltip title={
            healthStatus === 'error' ? 'Service health critical - check Service Health tab' :
            healthStatus === 'warning' ? 'Service warnings detected' :
            'All services healthy'
          }>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FiberManualRecordIcon 
                color={healthStatus} 
                sx={{ fontSize: 12 }} 
              />
              <Typography variant="body2" color="text.secondary">
                Service Health
              </Typography>
            </Box>
          </Tooltip>

          {/* Recording Toggle */}
          <Tooltip title={recordingEnabled ? "Recording ON - Data is being saved to database" : "Recording OFF - Data will NOT be saved"}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <FiberManualRecordIcon 
                color={recordingEnabled ? 'success' : 'default'} 
                sx={{ fontSize: 12 }} 
              />
              <Typography variant="body2" color="text.secondary">
                Recording
              </Typography>
              <Switch 
                size="small" 
                checked={recordingEnabled} 
                onChange={handleRecordingToggle}
                disabled={!isLiveMode}
              />
            </Box>
          </Tooltip>

          {/* RIGHT: Operator + Theme Toggle */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <Tooltip title="Change operator name in Settings">
              <Typography variant="body2" color="text.secondary">
                Operator: <Box component="span" color="text.primary">{settings.operatorName}</Box>
              </Typography>
            </Tooltip>
            {onToggleTheme && (
              <Tooltip title={isDarkMode ? 'Switch to light mode' : 'Switch to dark mode'}>
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
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
          mt: 8,
          backgroundColor: 'background.default',
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}
