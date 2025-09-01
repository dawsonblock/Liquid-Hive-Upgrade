import React from 'react';
import { ThemeProvider, createTheme } from '@mui/material/styles';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import Drawer from '@mui/material/Drawer';
import List from '@mui/material/List';
import ListItem from '@mui/material/ListItem';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemIcon from '@mui/material/ListItemIcon';
import ListItemText from '@mui/material/ListItemText';
import ChatIcon from '@mui/icons-material/Chat';
import StreamIcon from '@mui/icons-material/PlayArrow';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SettingsIcon from '@mui/icons-material/Settings';
import Toolbar from '@mui/material/Toolbar';
import AppBar from '@mui/material/AppBar';
import Typography from '@mui/material/Typography';
import { useState } from 'react';
import ChatPanel from './components/ChatPanel';
import StreamingChatPanel from './components/StreamingChatPanel';
import SystemPanel from './components/SystemPanel';
import ForgePanel from './components/ForgePanel';
import { Provider } from 'react-redux';
import { store } from './store';

const drawerWidth = 240;

const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#0ea5e9',
    },
    secondary: {
      main: '#e11d48',
    },
  },
});

export default function App() {
  const [panel, setPanel] = useState<'chat' | 'streaming' | 'system' | 'forge'>('streaming');
  return (
    <Provider store={store}>
      <ThemeProvider theme={darkTheme}>
        <CssBaseline />
        <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
          <Toolbar>
            <Typography variant="h6" noWrap component="div">
              LIQUID-HIVE Enhanced Cognitive Console
            </Typography>
          </Toolbar>
        </AppBar>
        <Drawer
          variant="permanent"
          sx={{
            width: drawerWidth,
            flexShrink: 0,
            [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
          }}
        >
          <Toolbar />
          <List>
            <ListItem disablePadding>
              <ListItemButton selected={panel === 'streaming'} onClick={() => setPanel('streaming')}>
                <ListItemIcon><StreamIcon /></ListItemIcon>
                <ListItemText primary="Streaming Chat" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton selected={panel === 'chat'} onClick={() => setPanel('chat')}>
                <ListItemIcon><ChatIcon /></ListItemIcon>
                <ListItemText primary="Classic Chat" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton selected={panel === 'system'} onClick={() => setPanel('system')}>
                <ListItemIcon><DashboardIcon /></ListItemIcon>
                <ListItemText primary="System Console" />
              </ListItemButton>
            </ListItem>
            <ListItem disablePadding>
              <ListItemButton selected={panel === 'forge'} onClick={() => setPanel('forge')}>
                <ListItemIcon><SettingsIcon /></ListItemIcon>
                <ListItemText primary="Cognitive Forge" />
              </ListItemButton>
            </ListItem>
          </List>
        </Drawer>
        <Box component="main" sx={{ flexGrow: 1, p: 3, ml: `${drawerWidth}px` }}>
          <Toolbar />
          {panel === 'streaming' && <StreamingChatPanel />}
          {panel === 'chat' && <ChatPanel />}
          {panel === 'system' && <SystemPanel />}
          {panel === 'forge' && <ForgePanel />}
        </Box>
      </ThemeProvider>
    </Provider>
  );
}