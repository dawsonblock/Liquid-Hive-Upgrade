import ChatIcon from '@mui/icons-material/Chat';
import DarkModeRoundedIcon from '@mui/icons-material/DarkModeRounded';
import DashboardIcon from '@mui/icons-material/Dashboard';
import MenuIcon from '@mui/icons-material/Menu';
import StreamIcon from '@mui/icons-material/PlayArrow';
import SettingsIcon from '@mui/icons-material/Settings';
import VpnKeyIcon from '@mui/icons-material/VpnKey';
import WbSunnyRoundedIcon from '@mui/icons-material/WbSunnyRounded';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CssBaseline from '@mui/material/CssBaseline';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import Stack from '@mui/material/Stack';
import { ThemeProvider, createTheme, responsiveFontSizes } from '@mui/material/styles';
import Toolbar from '@mui/material/Toolbar';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useEffect, useMemo, useState } from 'react';
import { Provider } from 'react-redux';

import CacheAdminPanel from './components/CacheAdminPanel';
import ChatPanel from './components/ChatPanel';
import ForgePanel from './components/ForgePanel';
import SecretsPanel from './components/SecretsPanel';
import StreamingChatPanel from './components/StreamingChatPanel';
import SystemPanel from './components/SystemPanel';
import { ProvidersProvider, useProviders } from './contexts/ProvidersContext';
import { health } from './services/api';
import { store } from './store';

const drawerWidth = 260;

function useBackendHealth(pollMs = 5000) {
  const [online, setOnline] = useState<boolean>(true);
  useEffect(() => {
    let active = true;
    const run = async () => {
      const res = await health();
      if (!active) return;
      setOnline(!!res.ok);
    };
    run();
    const id = setInterval(run, pollMs);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [pollMs]);
  return online;
}

export default function App() {
  const prefersDark = useMediaQuery('(prefers-color-scheme: dark)');
  const [mode, setMode] = useState<'dark' | 'light'>(prefersDark ? 'dark' : 'light');
  const theme = useMemo(
    () =>
      responsiveFontSizes(
        createTheme({
          palette: {
            mode,
            primary: { main: '#1a73e8' },
            secondary: { main: '#10b981' },
            background: {
              default: mode === 'dark' ? '#0b1220' : '#f7f9fc',
              paper: mode === 'dark' ? '#0f172a' : '#ffffff',
            },
          },
          shape: { borderRadius: 14 },
          typography: {
            fontFamily: [
              'Inter',
              'ui-sans-serif',
              'system-ui',
              '-apple-system',
              'Segoe UI',
              'Roboto',
              'Helvetica Neue',
              'Arial',
              'Noto Sans',
              'Apple Color Emoji',
              'Segoe UI Emoji',
              'Segoe UI Symbol',
            ].join(','),
            h6: { fontWeight: 600 },
          },
          components: {
            MuiPaper: {
              styleOverrides: {
                root: ({ theme }) => ({
                  transition: 'box-shadow .2s ease',
                  boxShadow: theme.palette.mode === 'dark' ? 'none' : '0 1px 2px rgba(0,0,0,0.06)',
                }),
              },
            },
            MuiButton: {
              defaultProps: { disableElevation: true },
            },
          },
        })
      ),
    [mode]
  );

  const [panel, setPanel] = useState<
    'chat' | 'streaming' | 'system' | 'forge' | 'secrets' | 'cache'
  >('streaming');
  const [mobileOpen, setMobileOpen] = useState(false);
  const isMdUp = useMediaQuery('(min-width:900px)');
  const online = useBackendHealth();
  return (
    <Provider store={store}>
      <ProvidersProvider>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <AppBar
            position='fixed'
            color='transparent'
            elevation={0}
            sx={{
              backdropFilter: 'blur(10px)',
              WebkitBackdropFilter: 'blur(10px)',
              bgcolor: t =>
                t.palette.mode === 'dark' ? 'rgba(2,6,23,0.6)' : 'rgba(255,255,255,0.7)',
              borderBottom: t => `1px solid ${t.palette.divider}`,
              zIndex: t => t.zIndex.drawer + 1,
            }}
          >
            <Toolbar>
              {!isMdUp && (
                <IconButton
                  color='inherit'
                  edge='start'
                  onClick={() => setMobileOpen(v => !v)}
                  sx={{ mr: 1 }}
                >
                  <MenuIcon />
                </IconButton>
              )}
              <Stack
                direction='row'
                spacing={1.25}
                alignItems='center'
                sx={{ flexGrow: 1, minWidth: 0 }}
              >
                <Box
                  component='img'
                  src='/logo.svg'
                  alt='Liquid Hive'
                  sx={{ width: 28, height: 28, borderRadius: 1 }}
                />
                <Typography
                  variant='h6'
                  noWrap
                  component='div'
                  sx={{ fontWeight: 700, letterSpacing: 0.2 }}
                >
                  <Box
                    component='span'
                    sx={{
                      background: t =>
                        t.palette.mode === 'dark'
                          ? 'linear-gradient(90deg,#60a5fa 0%,#34d399 50%,#22d3ee 100%)'
                          : 'linear-gradient(90deg,#1a73e8 0%,#10b981 50%,#06b6d4 100%)',
                      WebkitBackgroundClip: 'text',
                      WebkitTextFillColor: 'transparent',
                    }}
                  >
                    LIQUID‑HIVE
                  </Box>{' '}
                  Console
                </Typography>
              </Stack>
              {/* Backend online/offline */}
              <Tooltip title={online ? 'Backend online' : 'Backend offline'}>
                <Chip
                  size='small'
                  label={online ? 'Online' : 'Offline'}
                  color={online ? 'success' : 'error'}
                  sx={{ mr: 1 }}
                />
              </Tooltip>
              {/* Providers polling indicator */}
              <HeaderPollingChip />
              <Tooltip title={mode === 'dark' ? 'Switch to light' : 'Switch to dark'}>
                <IconButton
                  color='inherit'
                  onClick={() => setMode(m => (m === 'dark' ? 'light' : 'dark'))}
                >
                  {mode === 'dark' ? <WbSunnyRoundedIcon /> : <DarkModeRoundedIcon />}
                </IconButton>
              </Tooltip>
            </Toolbar>
          </AppBar>
          <Drawer
            variant={isMdUp ? 'permanent' : 'temporary'}
            open={isMdUp ? true : mobileOpen}
            onClose={() => setMobileOpen(false)}
            ModalProps={{ keepMounted: true }}
            sx={{
              display: 'block',
              [`& .MuiDrawer-paper`]: {
                width: drawerWidth,
                boxSizing: 'border-box',
                borderRight: t => `1px solid ${t.palette.divider}`,
                backgroundImage: t =>
                  t.palette.mode === 'dark'
                    ? 'linear-gradient(180deg, rgba(2,6,23,1) 0%, rgba(15,23,42,1) 100%)'
                    : 'linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(247,249,252,1) 100%)',
              },
            }}
          >
            <Toolbar />
            <List>
              <ListItem disablePadding>
                <ListItemButton
                  selected={panel === 'streaming'}
                  onClick={() => setPanel('streaming')}
                >
                  <ListItemIcon>
                    <StreamIcon />
                  </ListItemIcon>
                  <ListItemText primary='Streaming Chat' />
                </ListItemButton>
              </ListItem>
              <ListItem disablePadding>
                <ListItemButton selected={panel === 'chat'} onClick={() => setPanel('chat')}>
                  <ListItemIcon>
                    <ChatIcon />
                  </ListItemIcon>
                  <ListItemText primary='Classic Chat' />
                </ListItemButton>
              </ListItem>
              <Divider sx={{ my: 1 }} />
              <ListItem disablePadding>
                <ListItemButton selected={panel === 'system'} onClick={() => setPanel('system')}>
                  <ListItemIcon>
                    <DashboardIcon />
                  </ListItemIcon>
                  <ListItemText primary='System Console' />
                </ListItemButton>
              </ListItem>
              <ListItem disablePadding>
                <ListItemButton selected={panel === 'cache'} onClick={() => setPanel('cache')}>
                  <ListItemIcon>
                    <SettingsIcon />
                  </ListItemIcon>
                  <ListItemText primary='Cache Admin' />
                </ListItemButton>
              </ListItem>
              <ListItem disablePadding>
                <ListItemButton selected={panel === 'secrets'} onClick={() => setPanel('secrets')}>
                  <ListItemIcon>
                    <VpnKeyIcon />
                  </ListItemIcon>
                  <ListItemText primary='Secrets' />
                </ListItemButton>
              </ListItem>
              <ListItem disablePadding>
                <ListItemButton selected={panel === 'forge'} onClick={() => setPanel('forge')}>
                  <ListItemIcon>
                    <SettingsIcon />
                  </ListItemIcon>
                  <ListItemText primary='Cognitive Forge' />
                </ListItemButton>
              </ListItem>
            </List>
          </Drawer>
          <Box
            component='main'
            sx={{
              flexGrow: 1,
              p: { xs: 2, md: 3 },
              ml: { xs: 0, md: `${drawerWidth}px` },
              minHeight: '100vh',
              background: t =>
                t.palette.mode === 'dark'
                  ? 'radial-gradient(1200px 600px at -200px -200px, rgba(29,78,216,0.20), transparent), radial-gradient(800px 400px at 120% 10%, rgba(16,185,129,0.16), transparent)'
                  : 'radial-gradient(1200px 600px at -200px -200px, rgba(26,115,232,0.08), transparent), radial-gradient(800px 400px at 120% 10%, rgba(16,185,129,0.06), transparent)',
            }}
          >
            <Toolbar />
            <Box sx={{ mx: 'auto', width: '100%', maxWidth: 1200 }}>
              {panel === 'streaming' && <StreamingChatPanel />}
              {panel === 'chat' && <ChatPanel />}
              {panel === 'system' && <SystemPanel />}
              {panel === 'cache' && <CacheAdminPanel />}
              {panel === 'secrets' && <SecretsPanel />}
              {panel === 'forge' && <ForgePanel />}
            </Box>
          </Box>
        </ThemeProvider>
      </ProvidersProvider>
    </Provider>
  );
}

function HeaderPollingChip() {
  // Lightweight consumer for header; safe because ProvidersProvider wraps App
  const { autoRefresh, intervalMs } = useProviders();
  const label = autoRefresh ? `Polling ${Math.round(intervalMs / 1000)}s` : 'Polling off';
  const color: any = autoRefresh ? 'info' : 'default';
  return (
    <Tooltip title='Providers status polling'>
      <Chip size='small' label={label} color={color} variant='outlined' sx={{ mr: 1 }} />
    </Tooltip>
  );
}
