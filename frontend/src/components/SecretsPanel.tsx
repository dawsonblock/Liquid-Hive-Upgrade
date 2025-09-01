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
import RefreshIcon from '@mui/icons-material/Refresh';
import { getProvidersStatus, getSecretsHealth, reloadRouterSecrets, secretExists, setSecret } from '../services/api';

const SECRET_KEYS = [
    { key: 'DEEPSEEK_API_KEY', label: 'DeepSeek API Key', placeholder: 'sk-...' },
    { key: 'HUGGING_FACE_HUB_TOKEN', label: 'Hugging Face Token', placeholder: 'hf_...' },
    { key: 'GITHUB_TOKEN', label: 'GitHub Token', placeholder: 'ghp_...' }
];

export default function SecretsPanel() {
    const [adminToken, setAdminToken] = useState<string>('');
    const [values, setValues] = useState<Record<string, string>>({});
    const [exists, setExists] = useState<Record<string, boolean>>({});
    const [saving, setSaving] = useState<Record<string, boolean>>({});
    const [message, setMessage] = useState<string>('');
    const [error, setError] = useState<string>('');
    const [health, setHealth] = useState<any>(null);
    const [providers, setProviders] = useState<Record<string, any>>({});
    const [providersLoading, setProvidersLoading] = useState<boolean>(false);

    useEffect(() => {
        // Load health and existence of known secrets
        (async () => {
            try {
                const h = await getSecretsHealth();
                setHealth(h);
            } catch { }
            try {
                const ps = await getProvidersStatus();
                if (ps?.providers) setProviders(ps.providers);
            } catch { }
            for (const s of SECRET_KEYS) {
                try {
                    const r = await secretExists(s.key);
                    setExists(prev => ({ ...prev, [s.key]: !!r.exists }));
                } catch { }
            }
            // Prefill admin token from localStorage
            const t = localStorage.getItem('LH_ADMIN_TOKEN') || '';
            if (t) setAdminToken(t);
        })();
    }, []);

    const provider = useMemo(() => health?.active_provider || 'unknown', [health]);

    const onSave = async (name: string) => {
        setError(''); setMessage('');
        setSaving(p => ({ ...p, [name]: true }));
        try {
            const resp = await setSecret(name, values[name], adminToken || undefined);
            if (resp.error) {
                setError(resp.error + (resp.provider ? ` (provider: ${resp.provider})` : ''));
            } else {
                setMessage('Saved');
                setExists(p => ({ ...p, [name]: true }));
                // Persist admin token locally for convenience
                if (adminToken) localStorage.setItem('LH_ADMIN_TOKEN', adminToken);
            }
        } catch (e: any) {
            setError(e?.message || 'Failed to save');
        } finally {
            setSaving(p => ({ ...p, [name]: false }));
        }
    };

    const onReload = async () => {
        setError(''); setMessage('');
        try {
            const r = await reloadRouterSecrets(adminToken || undefined);
            if (r.error) setError(r.error);
            else {
                setMessage('Router reloaded');
                // Refresh providers after a short delay to allow warm-up
                setTimeout(async () => {
                    try {
                        setProvidersLoading(true);
                        const ps = await getProvidersStatus();
                        if (ps?.providers) setProviders(ps.providers);
                    } catch { } finally { setProvidersLoading(false); }
                }, 800);
            }
        } catch (e: any) {
            setError(e?.message || 'Failed to reload');
        }
    };

    const refreshProviders = async () => {
        try {
            setProvidersLoading(true);
            const ps = await getProvidersStatus();
            if (ps?.providers) setProviders(ps.providers);
        } catch { } finally { setProvidersLoading(false); }
    };

    return (
        <Box>
            <Typography variant="h5" gutterBottom>Secrets & API Tokens</Typography>
            <Typography variant="body2" color="text.secondary" gutterBottom>
                Provider: <b>{provider}</b>
            </Typography>
            <Alert severity="info" sx={{ mb: 2 }}>
                - Values are never echoed back. For AWS provider, writes are disabled; set them in AWS Secrets Manager.
            </Alert>
            <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
                <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
                    <TextField fullWidth label="Admin Token (optional)" value={adminToken}
                        onChange={e => setAdminToken(e.target.value)} placeholder="If ADMIN_TOKEN is set on the server" />
                    <Chip label={adminToken ? 'Provided' : 'Not set'} color={adminToken ? 'success' : 'default'} />
                </Stack>
            </Paper>

            <Grid container spacing={2}>
                {SECRET_KEYS.map(s => (
                    <Grid key={s.key} item xs={12} md={6}>
                        <Paper variant="outlined" sx={{ p: 2 }}>
                            <Stack spacing={1}>
                                <Stack direction="row" alignItems="center" spacing={1}>
                                    <Typography variant="subtitle1">{s.label}</Typography>
                                    <Chip size="small" label={exists[s.key] ? 'Configured' : 'Missing'} color={exists[s.key] ? 'success' : 'warning'} />
                                </Stack>
                                <TextField type="password" label={s.label} placeholder={s.placeholder}
                                    value={values[s.key] || ''}
                                    onChange={e => setValues(v => ({ ...v, [s.key]: e.target.value }))}
                                    fullWidth />
                                <Stack direction="row" spacing={1}>
                                    <Button variant="contained" disabled={saving[s.key] || !values[s.key]}
                                        onClick={() => onSave(s.key)}>
                                        {saving[s.key] ? 'Saving…' : 'Save'}
                                    </Button>
                                    <Divider orientation="vertical" flexItem />
                                    <Typography variant="caption" color="text.secondary">Key is stored securely server-side</Typography>
                                </Stack>
                            </Stack>
                        </Paper>
                    </Grid>
                ))}
            </Grid>

        {!!providers && Object.keys(providers).length > 0 && (
                <Paper variant="outlined" sx={{ p: 2, mt: 3 }}>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} alignItems={{ sm: 'center' }} justifyContent="space-between">
            <Typography variant="subtitle1">Provider Status</Typography>
            <Button size="small" variant="outlined" onClick={refreshProviders} startIcon={<RefreshIcon />}
                disabled={providersLoading}>{providersLoading ? 'Refreshing…' : 'Refresh'}</Button>
            </Stack>
                    <Grid container spacing={1}>
                        {Object.entries(providers).map(([name, info]) => (
                            <Grid key={name} item>
                                <Chip label={`${name}: ${info?.status || 'unknown'}`} color={(info?.status === 'healthy' ? 'success' : (info?.status ? 'warning' : 'default')) as any} />
                            </Grid>
                        ))}
                    </Grid>
                </Paper>
            )}

            {message && <Alert sx={{ mt: 2 }} severity="success">{message}</Alert>}
            {error && <Alert sx={{ mt: 2 }} severity="error">{error}</Alert>}
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 2 }}>
                <Button variant="outlined" onClick={onReload}>Reload Router (apply secrets)</Button>
            </Stack>
        </Box>
    );
}
