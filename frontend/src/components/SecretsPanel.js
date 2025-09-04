import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import RefreshIcon from '@mui/icons-material/Refresh';
import TimerIcon from '@mui/icons-material/Timer';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Select from '@mui/material/Select';
import Stack from '@mui/material/Stack';
import Switch from '@mui/material/Switch';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useEffect, useMemo, useState } from 'react';
import { useProviders } from '../contexts/ProvidersContext';
import { getSecretsHealth, reloadRouterSecrets, secretExists, setSecret, warmQwenProvider } from '../services/api';
const SECRET_KEYS = [
    { key: 'DEEPSEEK_API_KEY', label: 'DeepSeek API Key', placeholder: 'sk-...' },
    { key: 'HUGGING_FACE_HUB_TOKEN', label: 'Hugging Face Token', placeholder: 'hf_...' },
    { key: 'GITHUB_TOKEN', label: 'GitHub Token', placeholder: 'ghp_...' }
];
export default function SecretsPanel() {
    const [adminToken, setAdminToken] = useState('');
    const [values, setValues] = useState({});
    const [exists, setExists] = useState({});
    const [saving, setSaving] = useState({});
    const [message, setMessage] = useState('');
    const [error, setError] = useState('');
    const [health, setHealth] = useState(null);
    const { providers, loading: providersLoading, refresh: refreshProviders, autoRefresh, setAutoRefresh, intervalMs, setIntervalMs } = useProviders();
    const [qwenModel, setQwenModel] = useState('');
    const [qwenPreload, setQwenPreload] = useState(false);
    const [qwenAutoload, setQwenAutoload] = useState(false);
    const [warming, setWarming] = useState(false);
    useEffect(() => {
        // Load health and existence of known secrets
        (async () => {
            try {
                const h = await getSecretsHealth();
                setHealth(h);
            }
            catch { }
            try {
                await refreshProviders();
            }
            catch { }
            for (const s of SECRET_KEYS) {
                try {
                    const r = await secretExists(s.key);
                    setExists(prev => ({ ...prev, [s.key]: !!r.exists }));
                }
                catch { }
            }
            // Prefill admin token from localStorage
            const t = localStorage.getItem('LH_ADMIN_TOKEN') || '';
            if (t)
                setAdminToken(t);
            // Prefill Qwen settings from env exposure if present in provider info
            try {
                const qwen = (await getSecretsHealth());
                // not strictly available; we fallback to localStorage cache
            }
            catch { }
            // preload UI defaults from localStorage if present
            try {
                const qm = localStorage.getItem('LH_QWEN_CPU_MODEL');
                const qpl = localStorage.getItem('LH_QWEN_CPU_PRELOAD');
                const qal = localStorage.getItem('LH_QWEN_CPU_AUTOLOAD');
                if (qm)
                    setQwenModel(qm);
                if (qpl)
                    setQwenPreload(qpl === '1');
                if (qal)
                    setQwenAutoload(qal === '1');
            }
            catch { }
        })();
    }, []);
    const provider = useMemo(() => health?.active_provider || 'unknown', [health]);
    const onSave = async (name) => {
        setError('');
        setMessage('');
        setSaving(p => ({ ...p, [name]: true }));
        try {
            const resp = await setSecret(name, values[name], adminToken || undefined);
            if (resp.error) {
                setError(resp.error + (resp.provider ? ` (provider: ${resp.provider})` : ''));
            }
            else {
                setMessage('Saved');
                setExists(p => ({ ...p, [name]: true }));
                // Persist admin token locally for convenience
                if (adminToken)
                    localStorage.setItem('LH_ADMIN_TOKEN', adminToken);
            }
        }
        catch (e) {
            setError(e?.message || 'Failed to save');
        }
        finally {
            setSaving(p => ({ ...p, [name]: false }));
        }
    };
    const onReload = async () => {
        setError('');
        setMessage('');
        try {
            const r = await reloadRouterSecrets(adminToken || undefined);
            if (r.error)
                setError(r.error);
            else {
                setMessage('Router reloaded');
                // Refresh providers after a short delay to allow warm-up
                setTimeout(async () => {
                    try {
                        await refreshProviders();
                    }
                    catch { }
                }, 800);
            }
        }
        catch (e) {
            setError(e?.message || 'Failed to reload');
        }
    };
    const persistQwenUi = () => {
        try {
            localStorage.setItem('LH_QWEN_CPU_MODEL', qwenModel || '');
            localStorage.setItem('LH_QWEN_CPU_PRELOAD', qwenPreload ? '1' : '0');
            localStorage.setItem('LH_QWEN_CPU_AUTOLOAD', qwenAutoload ? '1' : '0');
        }
        catch { }
    };
    const applyQwenSettings = async () => {
        setError('');
        setMessage('');
        try {
            // Apply env-style secrets for Qwen provider
            const results = [];
            if (qwenModel) {
                const r = await setSecret('QWEN_CPU_MODEL', qwenModel, adminToken || undefined);
                results.push({ key: 'QWEN_CPU_MODEL', ok: !r.error });
            }
            const r2 = await setSecret('QWEN_CPU_PRELOAD', qwenPreload ? '1' : '0', adminToken || undefined);
            results.push({ key: 'QWEN_CPU_PRELOAD', ok: !r2.error });
            const r3 = await setSecret('QWEN_CPU_AUTOLOAD', qwenAutoload ? '1' : '0', adminToken || undefined);
            results.push({ key: 'QWEN_CPU_AUTOLOAD', ok: !r3.error });
            const anyError = results.some(x => !x.ok);
            if (anyError) {
                setError('Some Qwen settings failed to save');
            }
            else {
                setMessage('Qwen CPU settings saved');
            }
            persistQwenUi();
        }
        catch (e) {
            setError(e?.message || 'Failed to apply Qwen settings');
        }
    };
    const warmQwenNow = async () => {
        setError('');
        setMessage('');
        setWarming(true);
        try {
            const r = await warmQwenProvider(adminToken || undefined);
            if (r.error) {
                setError(r.error);
            }
            else {
                setMessage(r.status === 'already_loaded' ? 'Qwen already loaded' : (r.status === 'warmed' ? 'Qwen warmed' : 'Qwen warm failed'));
                // Refresh providers shortly after
                setTimeout(async () => { try {
                    await refreshProviders();
                }
                catch { } }, 800);
            }
        }
        catch (e) {
            setError(e?.message || 'Failed to warm Qwen');
        }
        finally {
            setWarming(false);
        }
    };
    // polling controlled by context
    return (_jsxs(Box, { children: [_jsx(Typography, { variant: "h5", gutterBottom: true, children: "Secrets & API Tokens" }), _jsxs(Typography, { variant: "body2", color: "text.secondary", gutterBottom: true, children: ["Provider: ", _jsx("b", { children: provider })] }), _jsx(Alert, { severity: "info", sx: { mb: 2 }, children: "- Values are never echoed back. For AWS provider, writes are disabled; set them in AWS Secrets Manager." }), _jsx(Paper, { variant: "outlined", sx: { p: 2, mb: 3 }, children: _jsxs(Stack, { direction: { xs: 'column', sm: 'row' }, spacing: 2, alignItems: { sm: 'center' }, children: [_jsx(TextField, { fullWidth: true, label: "Admin Token (optional)", value: adminToken, onChange: e => setAdminToken(e.target.value), placeholder: "If ADMIN_TOKEN is set on the server" }), _jsx(Chip, { label: adminToken ? 'Provided' : 'Not set', color: adminToken ? 'success' : 'default' })] }) }), _jsx(Grid, { container: true, spacing: 2, children: SECRET_KEYS.map(s => (_jsx(Grid, { item: true, xs: 12, md: 6, children: _jsx(Paper, { variant: "outlined", sx: { p: 2 }, children: _jsxs(Stack, { spacing: 1, children: [_jsxs(Stack, { direction: "row", alignItems: "center", spacing: 1, children: [_jsx(Typography, { variant: "subtitle1", children: s.label }), _jsx(Chip, { size: "small", label: exists[s.key] ? 'Configured' : 'Missing', color: exists[s.key] ? 'success' : 'warning' })] }), _jsx(TextField, { type: "password", label: s.label, placeholder: s.placeholder, value: values[s.key] || '', onChange: e => setValues(v => ({ ...v, [s.key]: e.target.value })), fullWidth: true }), _jsxs(Stack, { direction: "row", spacing: 1, children: [_jsx(Button, { variant: "contained", disabled: saving[s.key] || !values[s.key], onClick: () => onSave(s.key), children: saving[s.key] ? 'Saving…' : 'Save' }), _jsx(Divider, { orientation: "vertical", flexItem: true }), _jsx(Typography, { variant: "caption", color: "text.secondary", children: "Key is stored securely server-side" })] })] }) }) }, s.key))) }), _jsx(Paper, { variant: "outlined", sx: { p: 2, mt: 3 }, children: _jsxs(Stack, { direction: { xs: 'column', sm: 'row' }, spacing: 2, alignItems: { sm: 'center' }, children: [_jsxs(Stack, { direction: "row", spacing: 1, alignItems: "center", children: [_jsx(TimerIcon, { fontSize: "small" }), _jsx(Typography, { variant: "subtitle1", children: "Providers Polling" })] }), _jsxs(Stack, { direction: "row", spacing: 1, alignItems: "center", children: [_jsx(Typography, { variant: "caption", children: "Auto Refresh" }), _jsx(Switch, { size: "small", checked: !!autoRefresh, onChange: (e) => setAutoRefresh(e.target.checked) })] }), _jsxs(FormControl, { size: "small", sx: { minWidth: 160 }, children: [_jsx(InputLabel, { id: "poll-interval-label", children: "Interval" }), _jsxs(Select, { labelId: "poll-interval-label", label: "Interval", value: String(intervalMs), onChange: (e) => setIntervalMs(parseInt(e.target.value, 10)), children: [_jsx(MenuItem, { value: 5000, children: "5 seconds" }), _jsx(MenuItem, { value: 10000, children: "10 seconds" }), _jsx(MenuItem, { value: 15000, children: "15 seconds" }), _jsx(MenuItem, { value: 30000, children: "30 seconds" }), _jsx(MenuItem, { value: 60000, children: "60 seconds" })] })] })] }) }), _jsxs(Paper, { variant: "outlined", sx: { p: 2, mt: 3 }, children: [_jsx(Typography, { variant: "subtitle1", gutterBottom: true, children: "Qwen CPU Settings" }), _jsxs(Grid, { container: true, spacing: 2, children: [_jsx(Grid, { item: true, xs: 12, md: 6, children: _jsx(TextField, { fullWidth: true, label: "Model (QWEN_CPU_MODEL)", placeholder: "Qwen/Qwen2.5-0.5B-Instruct", value: qwenModel, onChange: (e) => setQwenModel(e.target.value) }) }), _jsx(Grid, { item: true, xs: 12, md: 3, children: _jsxs(Stack, { direction: "row", spacing: 1, alignItems: "center", sx: { height: '100%' }, children: [_jsx(Typography, { variant: "body2", children: "Preload" }), _jsx(Switch, { checked: qwenPreload, onChange: (e) => setQwenPreload(e.target.checked) })] }) }), _jsx(Grid, { item: true, xs: 12, md: 3, children: _jsxs(Stack, { direction: "row", spacing: 1, alignItems: "center", sx: { height: '100%' }, children: [_jsx(Typography, { variant: "body2", children: "Autoload on use" }), _jsx(Switch, { checked: qwenAutoload, onChange: (e) => setQwenAutoload(e.target.checked) })] }) })] }), _jsxs(Stack, { direction: { xs: 'column', sm: 'row' }, spacing: 1, sx: { mt: 2 }, children: [_jsx(Button, { variant: "outlined", onClick: applyQwenSettings, children: "Save Qwen Settings" }), _jsx(Button, { variant: "outlined", color: "secondary", onClick: onReload, children: "Reload Router" }), _jsx(Button, { variant: "contained", color: "primary", onClick: warmQwenNow, disabled: warming, children: warming ? 'Warming…' : 'Warm Qwen Now' })] }), _jsx(Typography, { variant: "caption", color: "text.secondary", sx: { display: 'block', mt: 1 }, children: "Preload loads the model at startup (may be slow). Autoload loads on first use. Leave both off to keep provider in \"initializing\" until you manually load." })] }), !!providers && Object.keys(providers).length > 0 && (_jsxs(Paper, { variant: "outlined", sx: { p: 2, mt: 3 }, children: [_jsxs(Stack, { direction: { xs: 'column', sm: 'row' }, spacing: 1, alignItems: { sm: 'center' }, justifyContent: "space-between", children: [_jsx(Typography, { variant: "subtitle1", children: "Provider Status" }), _jsx(Button, { size: "small", variant: "outlined", onClick: refreshProviders, startIcon: _jsx(RefreshIcon, {}), disabled: providersLoading, children: providersLoading ? 'Refreshing…' : 'Refresh' })] }), _jsx(Grid, { container: true, spacing: 1, children: Object.entries(providers).map(([name, info]) => (_jsx(Grid, { item: true, children: _jsx(Chip, { label: `${name}: ${info?.status || 'unknown'}`, color: (info?.status === 'healthy' ? 'success' : (info?.status ? 'warning' : 'default')) }) }, name))) })] })), message && _jsx(Alert, { sx: { mt: 2 }, severity: "success", children: message }), error && _jsx(Alert, { sx: { mt: 2 }, severity: "error", children: error }), _jsx(Stack, { direction: { xs: 'column', sm: 'row' }, spacing: 1, sx: { mt: 2 }, children: _jsx(Button, { variant: "outlined", onClick: onReload, children: "Reload Router (apply secrets)" }) })] }));
}
//# sourceMappingURL=SecretsPanel.js.map