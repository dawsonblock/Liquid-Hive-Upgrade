import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
    const [panel, setPanel] = useState('streaming');
    return (_jsx(Provider, { store: store, children: _jsxs(ThemeProvider, { theme: darkTheme, children: [_jsx(CssBaseline, {}), _jsx(AppBar, { position: "fixed", sx: { zIndex: (theme) => theme.zIndex.drawer + 1 }, children: _jsx(Toolbar, { children: _jsx(Typography, { variant: "h6", noWrap: true, component: "div", children: "LIQUID-HIVE Enhanced Cognitive Console" }) }) }), _jsxs(Drawer, { variant: "permanent", sx: {
                        width: drawerWidth,
                        flexShrink: 0,
                        [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
                    }, children: [_jsx(Toolbar, {}), _jsxs(List, { children: [_jsx(ListItem, { disablePadding: true, children: _jsxs(ListItemButton, { selected: panel === 'streaming', onClick: () => setPanel('streaming'), children: [_jsx(ListItemIcon, { children: _jsx(StreamIcon, {}) }), _jsx(ListItemText, { primary: "Streaming Chat" })] }) }), _jsx(ListItem, { disablePadding: true, children: _jsxs(ListItemButton, { selected: panel === 'chat', onClick: () => setPanel('chat'), children: [_jsx(ListItemIcon, { children: _jsx(ChatIcon, {}) }), _jsx(ListItemText, { primary: "Classic Chat" })] }) }), _jsx(ListItem, { disablePadding: true, children: _jsxs(ListItemButton, { selected: panel === 'system', onClick: () => setPanel('system'), children: [_jsx(ListItemIcon, { children: _jsx(DashboardIcon, {}) }), _jsx(ListItemText, { primary: "System Console" })] }) }), _jsx(ListItem, { disablePadding: true, children: _jsxs(ListItemButton, { selected: panel === 'forge', onClick: () => setPanel('forge'), children: [_jsx(ListItemIcon, { children: _jsx(SettingsIcon, {}) }), _jsx(ListItemText, { primary: "Cognitive Forge" })] }) })] })] }), _jsxs(Box, { component: "main", sx: { flexGrow: 1, p: 3, ml: `${drawerWidth}px` }, children: [_jsx(Toolbar, {}), panel === 'streaming' && _jsx(StreamingChatPanel, {}), panel === 'chat' && _jsx(ChatPanel, {}), panel === 'system' && _jsx(SystemPanel, {}), panel === 'forge' && _jsx(ForgePanel, {})] })] }) }));
}
