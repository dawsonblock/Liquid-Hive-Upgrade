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
import {
  getSecretsHealth,
  reloadRouterSecrets,
  secretExists,
  setSecret,
  warmQwenProvider,
} from '../services/api';

const SECRET_KEYS = [
  { key: 'DEEPSEEK_API_KEY', label: 'DeepSeek API Key', placeholder: 'sk-...' },
  { key: 'HUGGING_FACE_HUB_TOKEN', label: 'Hugging Face Token', placeholder: 'hf_...' },
  { key: 'GITHUB_TOKEN', label: 'GitHub Token', placeholder: 'ghp_...' },
];

export default function SecretsPanel() {
  const [adminToken, setAdminToken] = useState<string>('');
  const [values, setValues] = useState<Record<string, string>>({});
  const [exists, setExists] = useState<Record<string, boolean>>({});
  const [saving, setSaving] = useState<Record<string, boolean>>({});
  const [message, setMessage] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [health, setHealth] = useState<any>(null);
  const {
    providers,
    loading: providersLoading,
    refresh: refreshProviders,
    autoRefresh,
    setAutoRefresh,
    intervalMs,
    setIntervalMs,
  } = useProviders();
  const [qwenModel, setQwenModel] = useState<string>('');
  const [qwenPreload, setQwenPreload] = useState<boolean>(false);
  const [qwenAutoload, setQwenAutoload] = useState<boolean>(false);
  const [warming, setWarming] = useState<boolean>(false);

  useEffect(() => {
    // Load health and existence of known secrets
    (async () => {
      try {
        const h = await getSecretsHealth();
        setHealth(h);
      } catch {}
      try {
        await refreshProviders();
      } catch {}
      for (const s of SECRET_KEYS) {
        try {
          const r = await secretExists(s.key);
          setExists(prev => ({ ...prev, [s.key]: !!r.exists }));
        } catch {}
      }
      // Prefill admin token from localStorage
      const t = localStorage.getItem('LH_ADMIN_TOKEN') || '';
      if (t) setAdminToken(t);
      // Prefill Qwen settings from env exposure if present in provider info
      try {
        const qwen = await getSecretsHealth();
        // not strictly available; we fallback to localStorage cache
      } catch {}
      // preload UI defaults from localStorage if present
      try {
        const qm = localStorage.getItem('LH_QWEN_CPU_MODEL');
        const qpl = localStorage.getItem('LH_QWEN_CPU_PRELOAD');
        const qal = localStorage.getItem('LH_QWEN_CPU_AUTOLOAD');
        if (qm) setQwenModel(qm);
        if (qpl) setQwenPreload(qpl === '1');
        if (qal) setQwenAutoload(qal === '1');
      } catch {}
    })();
  }, []);

  const provider = useMemo(() => health?.active_provider || 'unknown', [health]);

  const onSave = async (name: string) => {
    setError('');
    setMessage('');
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
    setError('');
    setMessage('');
    try {
      const r = await reloadRouterSecrets(adminToken || undefined);
      if (r.error) setError(r.error);
      else {
        setMessage('Router reloaded');
        // Refresh providers after a short delay to allow warm-up
        setTimeout(async () => {
          try {
            await refreshProviders();
          } catch {}
        }, 800);
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to reload');
    }
  };

  const persistQwenUi = () => {
    try {
      localStorage.setItem('LH_QWEN_CPU_MODEL', qwenModel || '');
      localStorage.setItem('LH_QWEN_CPU_PRELOAD', qwenPreload ? '1' : '0');
      localStorage.setItem('LH_QWEN_CPU_AUTOLOAD', qwenAutoload ? '1' : '0');
    } catch {}
  };

  const applyQwenSettings = async () => {
    setError('');
    setMessage('');
    try {
      // Apply env-style secrets for Qwen provider
      const results: Array<{ key: string; ok: boolean }> = [];
      if (qwenModel) {
        const r = await setSecret('QWEN_CPU_MODEL', qwenModel, adminToken || undefined);
        results.push({ key: 'QWEN_CPU_MODEL', ok: !r.error });
      }
      const r2 = await setSecret(
        'QWEN_CPU_PRELOAD',
        qwenPreload ? '1' : '0',
        adminToken || undefined
      );
      results.push({ key: 'QWEN_CPU_PRELOAD', ok: !r2.error });
      const r3 = await setSecret(
        'QWEN_CPU_AUTOLOAD',
        qwenAutoload ? '1' : '0',
        adminToken || undefined
      );
      results.push({ key: 'QWEN_CPU_AUTOLOAD', ok: !r3.error });

      const anyError = results.some(x => !x.ok);
      if (anyError) {
        setError('Some Qwen settings failed to save');
      } else {
        setMessage('Qwen CPU settings saved');
      }
      persistQwenUi();
    } catch (e: any) {
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
      } else {
        setMessage(
          r.status === 'already_loaded'
            ? 'Qwen already loaded'
            : r.status === 'warmed'
              ? 'Qwen warmed'
              : 'Qwen warm failed'
        );
        // Refresh providers shortly after
        setTimeout(async () => {
          try {
            await refreshProviders();
          } catch {}
        }, 800);
      }
    } catch (e: any) {
      setError(e?.message || 'Failed to warm Qwen');
    } finally {
      setWarming(false);
    }
  };
  // polling controlled by context

  return (
    <Box>
      <Typography variant='h5' gutterBottom>
        Secrets & API Tokens
      </Typography>
      <Typography variant='body2' color='text.secondary' gutterBottom>
        Provider: <b>{provider}</b>
      </Typography>
      <Alert severity='info' sx={{ mb: 2 }}>
        - Values are never echoed back. For AWS provider, writes are disabled; set them in AWS
        Secrets Manager.
      </Alert>
      <Paper variant='outlined' sx={{ p: 2, mb: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
          <TextField
            fullWidth
            label='Admin Token (optional)'
            value={adminToken}
            onChange={e => setAdminToken(e.target.value)}
            placeholder='If ADMIN_TOKEN is set on the server'
          />
          <Chip
            label={adminToken ? 'Provided' : 'Not set'}
            color={adminToken ? 'success' : 'default'}
          />
        </Stack>
      </Paper>

      <Grid container spacing={2}>
        {SECRET_KEYS.map(s => (
          <Grid key={s.key} item xs={12} md={6}>
            <Paper variant='outlined' sx={{ p: 2 }}>
              <Stack spacing={1}>
                <Stack direction='row' alignItems='center' spacing={1}>
                  <Typography variant='subtitle1'>{s.label}</Typography>
                  <Chip
                    size='small'
                    label={exists[s.key] ? 'Configured' : 'Missing'}
                    color={exists[s.key] ? 'success' : 'warning'}
                  />
                </Stack>
                <TextField
                  type='password'
                  label={s.label}
                  placeholder={s.placeholder}
                  value={values[s.key] || ''}
                  onChange={e => setValues(v => ({ ...v, [s.key]: e.target.value }))}
                  fullWidth
                />
                <Stack direction='row' spacing={1}>
                  <Button
                    variant='contained'
                    disabled={saving[s.key] || !values[s.key]}
                    onClick={() => onSave(s.key)}
                  >
                    {saving[s.key] ? 'Saving…' : 'Save'}
                  </Button>
                  <Divider orientation='vertical' flexItem />
                  <Typography variant='caption' color='text.secondary'>
                    Key is stored securely server-side
                  </Typography>
                </Stack>
              </Stack>
            </Paper>
          </Grid>
        ))}
      </Grid>

      {/* Polling controls */}
      <Paper variant='outlined' sx={{ p: 2, mt: 3 }}>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems={{ sm: 'center' }}>
          <Stack direction='row' spacing={1} alignItems='center'>
            <TimerIcon fontSize='small' />
            <Typography variant='subtitle1'>Providers Polling</Typography>
          </Stack>
          <Stack direction='row' spacing={1} alignItems='center'>
            <Typography variant='caption'>Auto Refresh</Typography>
            <Switch
              size='small'
              checked={!!autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)}
            />
          </Stack>
          <FormControl size='small' sx={{ minWidth: 160 }}>
            <InputLabel id='poll-interval-label'>Interval</InputLabel>
            <Select
              labelId='poll-interval-label'
              label='Interval'
              value={String(intervalMs)}
              onChange={e => setIntervalMs(parseInt(e.target.value as string, 10))}
            >
              <MenuItem value={5000}>5 seconds</MenuItem>
              <MenuItem value={10000}>10 seconds</MenuItem>
              <MenuItem value={15000}>15 seconds</MenuItem>
              <MenuItem value={30000}>30 seconds</MenuItem>
              <MenuItem value={60000}>60 seconds</MenuItem>
            </Select>
          </FormControl>
        </Stack>
      </Paper>

      {/* Qwen CPU settings */}
      <Paper variant='outlined' sx={{ p: 2, mt: 3 }}>
        <Typography variant='subtitle1' gutterBottom>
          Qwen CPU Settings
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} md={6}>
            <TextField
              fullWidth
              label='Model (QWEN_CPU_MODEL)'
              placeholder='Qwen/Qwen2.5-0.5B-Instruct'
              value={qwenModel}
              onChange={e => setQwenModel(e.target.value)}
            />
          </Grid>
          <Grid item xs={12} md={3}>
            <Stack direction='row' spacing={1} alignItems='center' sx={{ height: '100%' }}>
              <Typography variant='body2'>Preload</Typography>
              <Switch checked={qwenPreload} onChange={e => setQwenPreload(e.target.checked)} />
            </Stack>
          </Grid>
          <Grid item xs={12} md={3}>
            <Stack direction='row' spacing={1} alignItems='center' sx={{ height: '100%' }}>
              <Typography variant='body2'>Autoload on use</Typography>
              <Switch checked={qwenAutoload} onChange={e => setQwenAutoload(e.target.checked)} />
            </Stack>
          </Grid>
        </Grid>
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 2 }}>
          <Button variant='outlined' onClick={applyQwenSettings}>
            Save Qwen Settings
          </Button>
          <Button variant='outlined' color='secondary' onClick={onReload}>
            Reload Router
          </Button>
          <Button variant='contained' color='primary' onClick={warmQwenNow} disabled={warming}>
            {warming ? 'Warming…' : 'Warm Qwen Now'}
          </Button>
        </Stack>
        <Typography variant='caption' color='text.secondary' sx={{ display: 'block', mt: 1 }}>
          Preload loads the model at startup (may be slow). Autoload loads on first use. Leave both
          off to keep provider in "initializing" until you manually load.
        </Typography>
      </Paper>

      {!!providers && Object.keys(providers).length > 0 && (
        <Paper variant='outlined' sx={{ p: 2, mt: 3 }}>
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1}
            alignItems={{ sm: 'center' }}
            justifyContent='space-between'
          >
            <Typography variant='subtitle1'>Provider Status</Typography>
            <Button
              size='small'
              variant='outlined'
              onClick={refreshProviders}
              startIcon={<RefreshIcon />}
              disabled={providersLoading}
            >
              {providersLoading ? 'Refreshing…' : 'Refresh'}
            </Button>
          </Stack>
          <Grid container spacing={1}>
            {Object.entries(providers).map(([name, info]) => (
              <Grid key={name} item>
                <Chip
                  label={`${name}: ${info?.status || 'unknown'}`}
                  color={
                    (info?.status === 'healthy'
                      ? 'success'
                      : info?.status
                        ? 'warning'
                        : 'default') as any
                  }
                />
              </Grid>
            ))}
          </Grid>
        </Paper>
      )}

      {message && (
        <Alert sx={{ mt: 2 }} severity='success'>
          {message}
        </Alert>
      )}
      {error && (
        <Alert sx={{ mt: 2 }} severity='error'>
          {error}
        </Alert>
      )}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 2 }}>
        <Button variant='outlined' onClick={onReload}>
          Reload Router (apply secrets)
        </Button>
      </Stack>
    </Box>
  );
}
