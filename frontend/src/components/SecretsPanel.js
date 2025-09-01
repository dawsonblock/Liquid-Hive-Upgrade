import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Stack from '@mui/material/Stack';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';
import { useEffect, useMemo, useState } from 'react';
import { getProvidersStatus, getSecretsHealth, reloadRouterSecrets, secretExists, setSecret } from '../services/api';
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
    const [providers, setProviders] = useState({});
    useEffect(() => {
        // Load health and existence of known secrets
        (async () => {
            try {
                const h = await getSecretsHealth();
                setHealth(h);
            }
            catch { }
            try {
                const ps = await getProvidersStatus();
                if (ps?.providers)
                    setProviders(ps.providers);
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
                        const ps = await getProvidersStatus();
                        if (ps?.providers)
                            setProviders(ps.providers);
                    }
                    catch { }
                }, 800);
            }
        }
        catch (e) {
            setError(e?.message || 'Failed to reload');
        }
    };
    return (_jsxs(Box, { children: [_jsx(Typography, { variant: "h5", gutterBottom: true, children: "Secrets & API Tokens" }), _jsxs(Typography, { variant: "body2", color: "text.secondary", gutterBottom: true, children: ["Provider: ", _jsx("b", { children: provider })] }), _jsx(Alert, { severity: "info", sx: { mb: 2 }, children: "- Values are never echoed back. For AWS provider, writes are disabled; set them in AWS Secrets Manager." }), _jsx(Paper, { variant: "outlined", sx: { p: 2, mb: 3 }, children: _jsxs(Stack, { direction: { xs: 'column', sm: 'row' }, spacing: 2, alignItems: { sm: 'center' }, children: [_jsx(TextField, { fullWidth: true, label: "Admin Token (optional)", value: adminToken, onChange: e => setAdminToken(e.target.value), placeholder: "If ADMIN_TOKEN is set on the server" }), _jsx(Chip, { label: adminToken ? 'Provided' : 'Not set', color: adminToken ? 'success' : 'default' })] }) }), _jsx(Grid, { container: true, spacing: 2, children: SECRET_KEYS.map(s => (_jsx(Grid, { item: true, xs: 12, md: 6, children: _jsx(Paper, { variant: "outlined", sx: { p: 2 }, children: _jsxs(Stack, { spacing: 1, children: [_jsxs(Stack, { direction: "row", alignItems: "center", spacing: 1, children: [_jsx(Typography, { variant: "subtitle1", children: s.label }), _jsx(Chip, { size: "small", label: exists[s.key] ? 'Configured' : 'Missing', color: exists[s.key] ? 'success' : 'warning' })] }), _jsx(TextField, { type: "password", label: s.label, placeholder: s.placeholder, value: values[s.key] || '', onChange: e => setValues(v => ({ ...v, [s.key]: e.target.value })), fullWidth: true }), _jsxs(Stack, { direction: "row", spacing: 1, children: [_jsx(Button, { variant: "contained", disabled: saving[s.key] || !values[s.key], onClick: () => onSave(s.key), children: saving[s.key] ? 'Saving…' : 'Save' }), _jsx(Divider, { orientation: "vertical", flexItem: true }), _jsx(Typography, { variant: "caption", color: "text.secondary", children: "Key is stored securely server-side" })] })] }) }) }, s.key))) }), !!providers && Object.keys(providers).length > 0 && (_jsxs(Paper, { variant: "outlined", sx: { p: 2, mt: 3 }, children: [_jsx(Typography, { variant: "subtitle1", gutterBottom: true, children: "Provider Status" }), _jsx(Grid, { container: true, spacing: 1, children: Object.entries(providers).map(([name, info]) => (_jsx(Grid, { item: true, children: _jsx(Chip, { label: `${name}: ${info?.status || 'unknown'}`, color: (info?.status === 'healthy' ? 'success' : (info?.status ? 'warning' : 'default')) }) }, name))) })] })), message && _jsx(Alert, { sx: { mt: 2 }, severity: "success", children: message }), error && _jsx(Alert, { sx: { mt: 2 }, severity: "error", children: error }), _jsx(Stack, { direction: { xs: 'column', sm: 'row' }, spacing: 1, sx: { mt: 2 }, children: _jsx(Button, { variant: "outlined", onClick: onReload, children: "Reload Router (apply secrets)" }) })] }));
}
