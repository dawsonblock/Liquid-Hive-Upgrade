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
    return (_jsxs(Grid, { container: true, spacing: 2, children: [_jsx(Grid, { item: true, xs: 12, children: _jsx(Paper, { variant: 'outlined', sx: { p: 2 }, children: _jsxs(Stack, { direction: 'row', spacing: 2, alignItems: 'center', children: [_jsx(Chip, { icon: _jsx(MemoryIcon, {}), label: `Semantic Cache ${healthy ? 'Healthy' : 'Unavailable'}`, color: healthy ? 'success' : 'default' }), analytics && (_jsxs(_Fragment, { children: [_jsx(Chip, { label: `Hit Rate: ${fmtPct(analytics.hit_rate)}`, color: (analytics.hit_rate || 0) > 0.5 ? 'success' : 'default', variant: 'outlined' }), _jsx(Chip, { label: `Entries: ${entries}`, variant: 'outlined' }), typeof analytics.avg_embedding_dim === 'number' && (_jsx(Chip, { label: `Dim: ${analytics.avg_embedding_dim}`, variant: 'outlined' }))] })), _jsx(Box, { flex: 1 }), _jsx(Button, { onClick: refreshAll, startIcon: loading ? _jsx(CircularProgress, { size: 16 }) : _jsx(RefreshIcon, {}), variant: 'outlined', size: 'small', children: "Refresh" })] }) }) }), _jsx(Grid, { item: true, xs: 12, md: 8, children: _jsxs(Paper, { variant: 'outlined', sx: { p: 2 }, children: [_jsx(Typography, { variant: 'subtitle1', gutterBottom: true, children: "Health" }), health ? (_jsxs(Stack, { spacing: 1, children: [_jsxs(Typography, { variant: 'body2', children: ["Status: ", _jsx("b", { children: health.status })] }), _jsxs(Typography, { variant: 'body2', children: ["Driver: ", _jsx("span", { style: smallMono, children: health.driver || health.backend || '—' })] }), health.strategy && (_jsxs(Typography, { variant: 'body2', children: ["Strategy: ", _jsx("b", { children: health.strategy })] })), typeof health.similarity_threshold === 'number' && (_jsxs(Typography, { variant: 'body2', children: ["Threshold: ", _jsx("b", { children: health.similarity_threshold })] })), health.redis_url && (_jsxs(Typography, { variant: 'body2', children: ["Redis: ", _jsx("span", { style: smallMono, children: health.redis_url })] })), typeof health.redis_connected === 'boolean' && (_jsxs(Typography, { variant: 'body2', children: ["Redis Connected: ", _jsx("b", { children: String(health.redis_connected) })] })), typeof health.in_memory === 'boolean' && (_jsxs(Typography, { variant: 'body2', children: ["In-Memory: ", _jsx("b", { children: String(health.in_memory) })] }))] })) : (_jsx(Typography, { variant: 'body2', color: 'text.secondary', children: "No health info." }))] }) }), _jsx(Grid, { item: true, xs: 12, md: 4, children: _jsxs(Paper, { variant: 'outlined', sx: { p: 2 }, children: [_jsx(Typography, { variant: 'subtitle1', gutterBottom: true, children: "Admin Actions" }), _jsxs(Stack, { spacing: 1, children: [_jsx(TextField, { label: 'Admin Token (optional)', size: 'small', value: adminToken, onChange: e => setAdminToken(e.target.value), type: 'password' }), _jsx(TextField, { label: 'Clear Pattern (optional)', size: 'small', placeholder: 'e.g., semantic_cache:*', value: pattern, onChange: e => setPattern(e.target.value) }), _jsx(Button, { variant: 'outlined', color: 'error', startIcon: clearing ? _jsx(CircularProgress, { size: 16 }) : _jsx(DeleteSweepIcon, {}), onClick: onClear, disabled: clearing, children: "Clear Cache" }), _jsxs(Stack, { direction: 'row', spacing: 1, alignItems: 'center', children: [_jsx(TextField, { label: 'Target Hit Rate', size: 'small', type: 'number', inputProps: { step: 0.05, min: 0.1, max: 0.9 }, value: targetHitRate, onChange: e => setTargetHitRate(Number(e.target.value)), sx: { width: 160 } }), _jsx(Button, { variant: 'outlined', startIcon: optimizing ? _jsx(CircularProgress, { size: 16 }) : _jsx(AutoFixHighIcon, {}), onClick: onOptimize, disabled: optimizing, children: "Optimize" })] }), _jsx(Button, { variant: 'outlined', startIcon: warming ? _jsx(CircularProgress, { size: 16 }) : _jsx(WhatshotIcon, {}), onClick: onWarm, disabled: warming, children: "Warm Cache" }), lastClear && (_jsx(Typography, { variant: 'caption', color: 'text.secondary', sx: { whiteSpace: 'pre-wrap' }, children: JSON.stringify(lastClear, null, 2) }))] })] }) }), _jsxs(Grid, { item: true, xs: 12, children: [error && _jsx(Alert, { severity: 'error', children: error }), status && (_jsxs(Paper, { variant: 'outlined', sx: { p: 2, mt: 2 }, children: [_jsx(Typography, { variant: 'subtitle1', gutterBottom: true, children: "Status" }), _jsx(Typography, { variant: 'caption', sx: { whiteSpace: 'pre-wrap' }, children: JSON.stringify(status, null, 2) })] })), report && (_jsxs(Paper, { variant: 'outlined', sx: { p: 2, mt: 2 }, children: [_jsx(Typography, { variant: 'subtitle1', gutterBottom: true, children: "Report" }), _jsx(Typography, { variant: 'caption', sx: { whiteSpace: 'pre-wrap' }, children: JSON.stringify(report, null, 2) })] }))] })] }));
};
export default CacheAdminPanel;
//# sourceMappingURL=CacheAdminPanel.js.map