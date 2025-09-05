import { jsx as _jsx, Fragment as _Fragment, jsxs as _jsxs } from "react/jsx-runtime";
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import MemoryIcon from '@mui/icons-material/Memory';
import RefreshIcon from '@mui/icons-material/Refresh';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import { Alert, Box, Button, Chip, CircularProgress, Grid, Paper, Stack, TextField, Typography, } from '@mui/material';
import { useCallback, useEffect, useState } from 'react';
import { clearCache, getCacheAnalytics, getCacheHealth, getCacheReport, getCacheStatus, optimizeCache, warmCache, } from '../services/api';
const fmtPct = (v) => typeof v === 'number' && !Number.isNaN(v) ? `${Math.round(v * 100)}%` : '—';
const smallMono = {
    fontFamily: 'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace',
};
const CacheAdminPanel = () => {
    const [health, setHealth] = useState(null);
    const [analytics, setAnalytics] = useState(null);
    const [loading, setLoading] = useState(false);
    const [pattern, setPattern] = useState('');
    const [adminToken, setAdminToken] = useState('');
    const [clearing, setClearing] = useState(false);
    const [lastClear, setLastClear] = useState(null);
    const [error, setError] = useState(null);
    const [targetHitRate, setTargetHitRate] = useState(0.6);
    const [optimizing, setOptimizing] = useState(false);
    const [warming, setWarming] = useState(false);
    const [report, setReport] = useState(null);
    const [status, setStatus] = useState(null);
    const refreshAll = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const [h, a, s] = await Promise.all([
                getCacheHealth().catch(() => null),
                getCacheAnalytics().catch(() => null),
                getCacheStatus().catch(() => null),
            ]);
            setHealth(h);
            setAnalytics(a);
            setStatus(s);
        }
        catch (e) {
            setError(e?.message || 'Failed to load cache status');
        }
        finally {
            setLoading(false);
        }
    }, []);
    useEffect(() => {
        refreshAll();
        const iv = setInterval(refreshAll, 30000);
        return () => clearInterval(iv);
    }, [refreshAll]);
    const onClear = async () => {
        setClearing(true);
        setError(null);
        try {
            const result = await clearCache(pattern.trim() || undefined, adminToken || undefined);
            setLastClear(result);
            await refreshAll();
        }
        catch (e) {
            setError(e?.message || 'Failed to clear cache');
        }
        finally {
            setClearing(false);
        }
    };
    const healthy = health?.semantic_cache === true ||
        (typeof health?.status === 'string' &&
            ['ok', 'healthy', 'ready'].includes(health.status.toLowerCase()));
    const entries = analytics?.total_entries ?? analytics?.current_size ?? '—';
    const onOptimize = async () => {
        setOptimizing(true);
        setError(null);
        try {
            await optimizeCache(targetHitRate);
            await refreshAll();
        }
        catch (e) {
            setError(e?.message || 'Failed to optimize cache');
        }
        finally {
            setOptimizing(false);
        }
    };
    const onWarm = async () => {
        setWarming(true);
        setError(null);
        try {
            await warmCache();
            await refreshAll();
            const rep = await getCacheReport().catch(() => null);
            setReport(rep);
        }
        catch (e) {
            setError(e?.message || 'Failed to warm cache');
        }
        finally {
            setWarming(false);
        }
    };
    return (
        <Grid container spacing={2}>
            <Grid item xs={12}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                    <Stack direction="row" spacing={2} alignItems="center">
                        <Chip
                            icon={<MemoryIcon />}
                            label={`Semantic Cache ${healthy ? 'Healthy' : 'Unavailable'}`}
                            color={healthy ? 'success' : 'default'}
                        />
                        {analytics && (
                            <>
                                <Chip
                                    label={`Hit Rate: ${fmtPct(analytics.hit_rate)}`}
                                    color={(analytics.hit_rate || 0) > 0.5 ? 'success' : 'default'}
                                    variant="outlined"
                                />
                                <Chip
                                    label={`Entries: ${entries}`}
                                    variant="outlined"
                                />
                                {typeof analytics.avg_embedding_dim === 'number' && (
                                    <Chip
                                        label={`Dim: ${analytics.avg_embedding_dim}`}
                                        variant="outlined"
                                    />
                                )}
                            </>
                        )}
                        <Box flex={1} />
                        <Button
                            onClick={refreshAll}
                            startIcon={loading ? <CircularProgress size={16} /> : <RefreshIcon />}
                            variant="outlined"
                            size="small"
                        >
                            Refresh
                        </Button>
                    </Stack>
                </Paper>
            </Grid>
            <Grid item xs={12} md={8}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                        Health
                    </Typography>
                    {health ? (
                        <Stack spacing={1}>
                            <Typography variant="body2">
                                Status: <b>{health.status}</b>
                            </Typography>
                            <Typography variant="body2">
                                Driver: <span style={smallMono}>{health.driver || health.backend || '—'}</span>
                            </Typography>
                            {health.strategy && (
                                <Typography variant="body2">
                                    Strategy: <b>{health.strategy}</b>
                                </Typography>
                            )}
                            {typeof health.similarity_threshold === 'number' && (
                                <Typography variant="body2">
                                    Threshold: <b>{health.similarity_threshold}</b>
                                </Typography>
                            )}
                            {health.redis_url && (
                                <Typography variant="body2">
                                    Redis: <span style={smallMono}>{health.redis_url}</span>
                                </Typography>
                            )}
                            {typeof health.redis_connected === 'boolean' && (
                                <Typography variant="body2">
                                    Redis Connected: <b>{String(health.redis_connected)}</b>
                                </Typography>
                            )}
                            {typeof health.in_memory === 'boolean' && (
                                <Typography variant="body2">
                                    In-Memory: <b>{String(health.in_memory)}</b>
                                </Typography>
                            )}
                        </Stack>
                    ) : (
                        <Typography variant="body2" color="text.secondary">
                            No health info.
                        </Typography>
                    )}
                </Paper>
            </Grid>
            <Grid item xs={12} md={4}>
                <Paper variant="outlined" sx={{ p: 2 }}>
                    <Typography variant="subtitle1" gutterBottom>
                        Admin Actions
                    </Typography>
                    <Stack spacing={1}>
                        <TextField
                            label="Admin Token (optional)"
                            size="small"
                            value={adminToken}
                            onChange={e => setAdminToken(e.target.value)}
                            type="password"
                        />
                        <TextField
                            label="Clear Pattern (optional)"
                            size="small"
                            placeholder="e.g., semantic_cache:*"
                            value={pattern}
                            onChange={e => setPattern(e.target.value)}
                        />
                        <Button
                            variant="outlined"
                            color="error"
                            startIcon={clearing ? <CircularProgress size={16} /> : <DeleteSweepIcon />}
                            onClick={onClear}
                            disabled={clearing}
                        >
                            Clear Cache
                        </Button>
                        <Stack direction="row" spacing={1} alignItems="center">
                            <TextField
                                label="Target Hit Rate"
                                size="small"
                                type="number"
                                inputProps={{ step: 0.05, min: 0.1, max: 0.9 }}
                                value={targetHitRate}
                                onChange={e => setTargetHitRate(Number(e.target.value))}
                                sx={{ width: 160 }}
                            />
                            <Button
                                variant="outlined"
                                startIcon={optimizing ? <CircularProgress size={16} /> : <AutoFixHighIcon />}
                                onClick={onOptimize}
                                disabled={optimizing}
                            >
                                Optimize
                            </Button>
                        </Stack>
                        <Button
                            variant="outlined"
                            startIcon={warming ? <CircularProgress size={16} /> : <WhatshotIcon />}
                            onClick={onWarm}
                            disabled={warming}
                        >
                            Warm Cache
                        </Button>
                        {lastClear && (
                            <Typography
                                variant="caption"
                                color="text.secondary"
                                sx={{ whiteSpace: 'pre-wrap' }}
                            >
                                {JSON.stringify(lastClear, null, 2)}
                            </Typography>
                        )}
                    </Stack>
                </Paper>
            </Grid>
            <Grid item xs={12}>
                {error && (
                    <Alert severity="error">{error}</Alert>
                )}
                {status && (
                    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
                        <Typography variant="subtitle1" gutterBottom>
                            Status
                        </Typography>
                        <Typography variant="caption" sx={{ whiteSpace: 'pre-wrap' }}>
                            {JSON.stringify(status, null, 2)}
                        </Typography>
                    </Paper>
                )}
                {report && (
                    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
                        <Typography variant="subtitle1" gutterBottom>
                            Report
                        </Typography>
                        <Typography variant="caption" sx={{ whiteSpace: 'pre-wrap' }}>
                            {JSON.stringify(report, null, 2)}
                        </Typography>
                    </Paper>
                )}
            </Grid>
        </Grid>
    );
};
export default CacheAdminPanel;
//# sourceMappingURL=CacheAdminPanel.js.map