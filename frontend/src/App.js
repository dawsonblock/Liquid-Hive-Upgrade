import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
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
import { ThemeProvider, createTheme, responsiveFontSizes } from '@mui/material/styles';
import Toolbar from '@mui/material/Toolbar';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import useMediaQuery from '@mui/material/useMediaQuery';
import { useEffect, useMemo, useState } from 'react';
import { Provider } from 'react-redux';
import ChatPanel from './components/ChatPanel';
import ForgePanel from './components/ForgePanel';
import SecretsPanel from './components/SecretsPanel';
import StreamingChatPanel from './components/StreamingChatPanel';
import SystemPanel from './components/SystemPanel';
import { health } from './services/api';
import { store } from './store';
const drawerWidth = 260;
function useBackendHealth(pollMs = 5000) {
    const [online, setOnline] = useState(true);
    useEffect(() => {
        let active = true;
        const run = async () => {
            const res = await health();
            if (!active)
                return;
            setOnline(!!res.ok);
        };
        run();
        const id = setInterval(run, pollMs);
        return () => { active = false; clearInterval(id); };
    }, [pollMs]);
    return online;
}
export default function App() {
    const prefersDark = useMediaQuery('(prefers-color-scheme: dark)');
    const [mode, setMode] = useState(prefersDark ? 'dark' : 'light');
    const theme = useMemo(() => responsiveFontSizes(createTheme({
        palette: {
            mode,
            primary: { main: '#0ea5e9' },
            secondary: { main: '#e11d48' },
            background: {
                default: mode === 'dark' ? '#0b1220' : '#f6f8fc',
                paper: mode === 'dark' ? '#0f172a' : '#ffffff'
            }
        },
        shape: { borderRadius: 12 }
    })), [mode]);
    const [panel, setPanel] = useState('streaming');
    const [mobileOpen, setMobileOpen] = useState(false);
    const isMdUp = useMediaQuery('(min-width:900px)');
    const online = useBackendHealth();
    return (_jsx(Provider, { store: store, children: _jsxs(ThemeProvider, { theme: theme, children: [_jsx(CssBaseline, {}), _jsx(AppBar, { position: "fixed", color: "transparent", elevation: 0, sx: {
                        backdropFilter: 'blur(8px)',
                        bgcolor: (t) => t.palette.mode === 'dark' ? 'rgba(2,6,23,0.6)' : 'rgba(255,255,255,0.6)',
                        borderBottom: (t) => `1px solid ${t.palette.divider}`,
                        zIndex: (t) => t.zIndex.drawer + 1
                    }, children: _jsxs(Toolbar, { children: [!isMdUp && (_jsx(IconButton, { color: "inherit", edge: "start", onClick: () => setMobileOpen(v => !v), sx: { mr: 1 }, children: _jsx(MenuIcon, {}) })), _jsx(Typography, { variant: "h6", noWrap: true, component: "div", sx: { flexGrow: 1 }, children: "LIQUID-HIVE Console" }), _jsx(Tooltip, { title: online ? 'Backend online' : 'Backend offline', children: _jsx(Chip, { size: "small", label: online ? 'Online' : 'Offline', color: online ? 'success' : 'error', sx: { mr: 1 } }) }), _jsx(Tooltip, { title: mode === 'dark' ? 'Switch to light' : 'Switch to dark', children: _jsx(IconButton, { color: "inherit", onClick: () => setMode(m => m === 'dark' ? 'light' : 'dark'), children: mode === 'dark' ? _jsx(WbSunnyRoundedIcon, {}) : _jsx(DarkModeRoundedIcon, {}) }) })] }) }), _jsxs(Drawer, { variant: isMdUp ? 'permanent' : 'temporary', open: isMdUp ? true : mobileOpen, onClose: () => setMobileOpen(false), ModalProps: { keepMounted: true }, sx: {
                        display: 'block',
                        [`& .MuiDrawer-paper`]: {
                            width: drawerWidth,
                            boxSizing: 'border-box',
                            borderRight: (t) => `1px solid ${t.palette.divider}`,
                            backgroundImage: (t) => t.palette.mode === 'dark'
                                ? 'linear-gradient(180deg, rgba(2,6,23,1) 0%, rgba(15,23,42,1) 100%)'
                                : 'linear-gradient(180deg, rgba(255,255,255,1) 0%, rgba(246,248,252,1) 100%)'
                        },
                    }, children: [_jsx(Toolbar, {}), _jsxs(List, { children: [_jsx(ListItem, { disablePadding: true, children: _jsxs(ListItemButton, { selected: panel === 'streaming', onClick: () => setPanel('streaming'), children: [_jsx(ListItemIcon, { children: _jsx(StreamIcon, {}) }), _jsx(ListItemText, { primary: "Streaming Chat" })] }) }), _jsx(ListItem, { disablePadding: true, children: _jsxs(ListItemButton, { selected: panel === 'chat', onClick: () => setPanel('chat'), children: [_jsx(ListItemIcon, { children: _jsx(ChatIcon, {}) }), _jsx(ListItemText, { primary: "Classic Chat" })] }) }), _jsx(Divider, { sx: { my: 1 } }), _jsx(ListItem, { disablePadding: true, children: _jsxs(ListItemButton, { selected: panel === 'system', onClick: () => setPanel('system'), children: [_jsx(ListItemIcon, { children: _jsx(DashboardIcon, {}) }), _jsx(ListItemText, { primary: "System Console" })] }) }), _jsx(ListItem, { disablePadding: true, children: _jsxs(ListItemButton, { selected: panel === 'secrets', onClick: () => setPanel('secrets'), children: [_jsx(ListItemIcon, { children: _jsx(VpnKeyIcon, {}) }), _jsx(ListItemText, { primary: "Secrets" })] }) }), _jsx(ListItem, { disablePadding: true, children: _jsxs(ListItemButton, { selected: panel === 'forge', onClick: () => setPanel('forge'), children: [_jsx(ListItemIcon, { children: _jsx(SettingsIcon, {}) }), _jsx(ListItemText, { primary: "Cognitive Forge" })] }) })] })] }), _jsxs(Box, { component: "main", sx: {
                        flexGrow: 1,
                        p: { xs: 2, md: 3 },
                        ml: { xs: 0, md: `${drawerWidth}px` },
                        minHeight: '100vh',
                        background: (t) => t.palette.mode === 'dark'
                            ? 'radial-gradient(1200px 600px at -200px -200px, rgba(14,165,233,0.12), transparent), radial-gradient(800px 400px at 120% 10%, rgba(225,29,72,0.10), transparent)'
                            : 'radial-gradient(1200px 600px at -200px -200px, rgba(14,165,233,0.06), transparent), radial-gradient(800px 400px at 120% 10%, rgba(225,29,72,0.05), transparent)'
                    }, children: [_jsx(Toolbar, {}), panel === 'streaming' && _jsx(StreamingChatPanel, {}), panel === 'chat' && _jsx(ChatPanel, {}), panel === 'system' && _jsx(SystemPanel, {}), panel === 'secrets' && _jsx(SecretsPanel, {}), panel === 'forge' && _jsx(ForgePanel, {})] })] }) }));
}
