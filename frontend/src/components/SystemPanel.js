import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from "react/jsx-runtime";
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import { Alert, Box, Button, Chip, Grid, IconButton, List, ListItem, ListItemText, Paper, Snackbar, Stack, TextField, Typography } from '@mui/material';
import { useEffect, useMemo, useState } from 'react';
import { approveProposal, denyProposal, fetchState, getApprovals, getSwarmStatus, previewAutopromote, setRouterThresholds } from '../services/api';
import { getBackendWsBase } from '../services/env';
const SystemPanel = () => {
    const [approvals, setApprovals] = useState([]);
    const [stateSummary, setStateSummary] = useState(null);
    const [events, setEvents] = useState([]);
    const [snack, setSnack] = useState([]);
    const [preview, setPreview] = useState([]);
    const [swarm, setSwarm] = useState(null);
    const [confThreshold, setConfThreshold] = useState('');
    const [supportThreshold, setSupportThreshold] = useState('');
    const [maxCot, setMaxCot] = useState('');
    const [adminToken, setAdminToken] = useState('');
    useEffect(() => {
        const load = async () => {
            try {
                setApprovals(await getApprovals());
                setStateSummary(await fetchState());
            }
            catch { }
        };
        load();
        const ws = new WebSocket(getBackendWsBase() + '/api/ws');
        ws.onmessage = (ev) => {
            try {
                const msg = JSON.parse(ev.data);
                if (msg.type === 'state_update')
                    setStateSummary(msg.payload);
                if (msg.type === 'approvals_update')
                    setApprovals(msg.payload);
                if (msg.type === 'autonomy_events') {
                    setEvents(msg.payload || []);
                    // Show a toast for each event
                    (msg.payload || []).forEach((e) => {
                        const text = e?.message || `Auto‑promotion: role ${e?.role} → ${e?.new_active}`;
                        setSnack(prev => [...prev, { open: true, msg: text }]);
                    });
                }
            }
            catch { }
        };
        return () => ws.close();
    }, []);
    useEffect(() => {
        const run = async () => {
            try {
                setSwarm(await getSwarmStatus());
            }
            catch { }
            try {
                // optional: pull current thresholds from stateSummary if exposed later
            }
            catch { }
        };
        run();
    }, []);
    const vitals = useMemo(() => stateSummary?.self_awareness_metrics || {}, [stateSummary]);
    const handlePreview = async () => {
        try {
            const res = await previewAutopromote();
            setPreview(res?.candidates || []);
            if (!res?.candidates?.length)
                setSnack(prev => [...prev, { open: true, msg: 'No auto‑promotion candidates at this time.' }]);
        }
        catch (e) {
            setSnack(prev => [...prev, { open: true, msg: 'Preview failed.' }]);
        }
    };
    const onApplyThresholds = async () => {
        const payload = {};
        if (confThreshold)
            payload.conf_threshold = Number(confThreshold);
        if (supportThreshold)
            payload.support_threshold = Number(supportThreshold);
        if (maxCot)
            payload.max_cot_tokens = Number(maxCot);
        try {
            const r = await setRouterThresholds(payload, adminToken || undefined);
            setSnack(prev => [...prev, { open: true, msg: r.error ? `Failed: ${r.error}` : 'Thresholds updated' }]);
        }
        catch {
            setSnack(prev => [...prev, { open: true, msg: 'Update failed' }]);
        }
    };
    return (_jsxs(_Fragment, { children: [_jsxs(Grid, { container: true, spacing: 2, children: [_jsx(Grid, { item: true, xs: 12, md: 6, children: _jsxs(Paper, { variant: "outlined", sx: { p: 2 }, children: [_jsxs(Stack, { direction: "row", spacing: 2, alignItems: "center", justifyContent: "space-between", children: [_jsx(Typography, { variant: "h6", children: "Core Vitals & Self\u2011Awareness (\u03A6)" }), _jsx(Button, { size: "small", variant: "outlined", onClick: handlePreview, children: "Preview Auto\u2011Promotions" })] }), _jsxs(Stack, { direction: "row", spacing: 2, sx: { mt: 1 }, children: [_jsx(Chip, { label: `Phi: ${vitals.phi ?? 'N/A'}`, color: "primary" }), _jsx(Chip, { label: `Memories: ${stateSummary?.memory_size ?? 'N/A'}` })] }), _jsxs(Box, { sx: { mt: 2 }, children: [_jsx(Typography, { variant: "subtitle2", children: "Operator Intent" }), _jsx(Typography, { variant: "body2", color: "text.secondary", children: stateSummary?.operator_intent ?? 'Unknown' })] }), preview.length > 0 && (_jsxs(Box, { sx: { mt: 2 }, children: [_jsx(Typography, { variant: "subtitle2", children: "Auto\u2011Promotion Candidates" }), _jsx(List, { dense: true, children: preview.map((p, i) => (_jsx(ListItem, { children: _jsx(ListItemText, { primary: `Role ${p.role}: ${p.challenger} vs ${p.active}`, secondary: `p95 ${p.p95_c?.toFixed?.(3)}s vs ${p.p95_a?.toFixed?.(3)}s; cost ${p.cost_c?.toFixed?.(6)} vs ${p.cost_a?.toFixed?.(6)}` }) }, i))) })] }))] }) }), _jsx(Grid, { item: true, xs: 12, md: 6, children: _jsxs(Paper, { variant: "outlined", sx: { p: 2 }, children: [_jsx(Typography, { variant: "h6", children: "Approval Queue" }), _jsxs(List, { children: [approvals.map((a) => (_jsx(ListItem, { secondaryAction: _jsxs(Box, { children: [_jsx(IconButton, { color: "success", onClick: async () => { await approveProposal(a.id); setApprovals(await getApprovals()); }, children: _jsx(CheckIcon, {}) }), _jsx(IconButton, { color: "error", onClick: async () => { await denyProposal(a.id); setApprovals(await getApprovals()); }, children: _jsx(CloseIcon, {}) })] }), children: _jsx(ListItemText, { primary: a.content }) }, a.id))), approvals.length === 0 && _jsx(Typography, { variant: "body2", color: "text.secondary", children: "No pending approvals." })] })] }) })] }), _jsxs(Grid, { container: true, spacing: 2, sx: { mt: 2 }, children: [_jsx(Grid, { item: true, xs: 12, md: 6, children: _jsxs(Paper, { variant: "outlined", sx: { p: 2 }, children: [_jsxs(Stack, { direction: "row", justifyContent: "space-between", alignItems: "center", children: [_jsx(Typography, { variant: "h6", children: "Swarm Status" }), _jsx(Button, { size: "small", variant: "outlined", onClick: async () => { try {
                                                setSwarm(await getSwarmStatus());
                                            }
                                            catch { } }, children: "Refresh" })] }), _jsx(Typography, { variant: "body2", sx: { mt: 1 }, children: swarm ? `Enabled: ${String(swarm.swarm_enabled)} • Nodes: ${swarm.active_nodes ?? 0}` : 'No swarm info' }), swarm?.nodes && (_jsx(Typography, { variant: "caption", sx: { whiteSpace: 'pre-wrap' }, children: JSON.stringify(swarm.nodes, null, 2) }))] }) }), _jsx(Grid, { item: true, xs: 12, md: 6, children: _jsxs(Paper, { variant: "outlined", sx: { p: 2 }, children: [_jsx(Typography, { variant: "h6", children: "Router Thresholds" }), _jsxs(Stack, { direction: { xs: 'column', sm: 'row' }, spacing: 1, sx: { mt: 1 }, children: [_jsx(TextField, { size: "small", label: "Conf", value: confThreshold, onChange: e => setConfThreshold(e.target.value), sx: { width: 120 } }), _jsx(TextField, { size: "small", label: "Support", value: supportThreshold, onChange: e => setSupportThreshold(e.target.value), sx: { width: 120 } }), _jsx(TextField, { size: "small", label: "Max CoT", value: maxCot, onChange: e => setMaxCot(e.target.value), sx: { width: 120 } })] }), _jsxs(Stack, { direction: { xs: 'column', sm: 'row' }, spacing: 1, sx: { mt: 1 }, children: [_jsx(TextField, { size: "small", label: "Admin Token", value: adminToken, onChange: e => setAdminToken(e.target.value), sx: { minWidth: 220 } }), _jsx(Button, { size: "small", variant: "outlined", onClick: onApplyThresholds, children: "Apply" })] }), _jsx(Typography, { variant: "caption", color: "text.secondary", children: "Requires ADMIN_TOKEN configured on server." })] }) })] }), snack.map((s, idx) => (_jsx(Snackbar, { open: s.open, autoHideDuration: 6000, onClose: () => setSnack(prev => prev.filter((_, i) => i !== idx)), children: _jsx(Alert, { onClose: () => setSnack(prev => prev.filter((_, i) => i !== idx)), severity: "info", sx: { width: '100%' }, children: s.msg }) }, idx)))] }));
};
export default SystemPanel;
