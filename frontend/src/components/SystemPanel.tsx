import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import { Alert, Box, Button, Chip, Grid, IconButton, List, ListItem, ListItemText, Paper, Snackbar, Stack, TextField, Typography } from '@mui/material';
import React, { useEffect, useMemo, useState } from 'react';
import { approveProposal, denyProposal, fetchState, getApprovals, previewAutopromote, getSwarmStatus, setRouterThresholds } from '../services/api';
import { getBackendWsBase } from '../services/env';

const SystemPanel: React.FC = () => {
  const [approvals, setApprovals] = useState<{ id: number; content: string }[]>([]);
  const [stateSummary, setStateSummary] = useState<any>(null);
  const [events, setEvents] = useState<any[]>([]);
  const [snack, setSnack] = useState<{ open: boolean; msg: string }[]>([]);
  const [preview, setPreview] = useState<any[]>([]);
  const [swarm, setSwarm] = useState<any>(null);
  const [confThreshold, setConfThreshold] = useState<string>('');
  const [supportThreshold, setSupportThreshold] = useState<string>('');
  const [maxCot, setMaxCot] = useState<string>('');
  const [adminToken, setAdminToken] = useState<string>('');

  useEffect(() => {
    const load = async () => {
      try {
        setApprovals(await getApprovals());
        setStateSummary(await fetchState());
      } catch { }
    };
    load();

    const ws = new WebSocket(getBackendWsBase() + '/api/ws');
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'state_update') setStateSummary(msg.payload);
        if (msg.type === 'approvals_update') setApprovals(msg.payload);
        if (msg.type === 'autonomy_events') {
          setEvents(msg.payload || []);
          // Show a toast for each event
          (msg.payload || []).forEach((e: any) => {
            const text = e?.message || `Auto‑promotion: role ${e?.role} → ${e?.new_active}`;
            setSnack(prev => [...prev, { open: true, msg: text }]);
          });
        }
      } catch { }
    };
    return () => ws.close();
  }, []);

  useEffect(() => {
    const run = async () => {
      try { setSwarm(await getSwarmStatus()); } catch {}
      try {
        // optional: pull current thresholds from stateSummary if exposed later
      } catch {}
    };
    run();
  }, []);

  const vitals = useMemo(() => stateSummary?.self_awareness_metrics || {}, [stateSummary]);

  const handlePreview = async () => {
    try {
      const res = await previewAutopromote();
      setPreview(res?.candidates || []);
      if (!res?.candidates?.length) setSnack(prev => [...prev, { open: true, msg: 'No auto‑promotion candidates at this time.' }]);
    } catch (e) {
      setSnack(prev => [...prev, { open: true, msg: 'Preview failed.' }]);
    }
  };

  const onApplyThresholds = async () => {
    const payload: any = {};
    if (confThreshold) payload.conf_threshold = Number(confThreshold);
    if (supportThreshold) payload.support_threshold = Number(supportThreshold);
    if (maxCot) payload.max_cot_tokens = Number(maxCot);
    try {
      const r = await setRouterThresholds(payload, adminToken || undefined);
      setSnack(prev => [...prev, { open: true, msg: r.error ? `Failed: ${r.error}` : 'Thresholds updated' }]);
    } catch {
      setSnack(prev => [...prev, { open: true, msg: 'Update failed' }]);
    }
  };

  return (
    <>
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
              <Typography variant="h6">Core Vitals & Self‑Awareness (Φ)</Typography>
              <Button size="small" variant="outlined" onClick={handlePreview}>Preview Auto‑Promotions</Button>
            </Stack>
            <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
              <Chip label={`Phi: ${vitals.phi ?? 'N/A'}`} color="primary" />
              <Chip label={`Memories: ${stateSummary?.memory_size ?? 'N/A'}`} />
            </Stack>
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2">Operator Intent</Typography>
              <Typography variant="body2" color="text.secondary">{stateSummary?.operator_intent ?? 'Unknown'}</Typography>
            </Box>
            {preview.length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography variant="subtitle2">Auto‑Promotion Candidates</Typography>
                <List dense>
                  {preview.map((p: any, i: number) => (
                    <ListItem key={i}>
                      <ListItemText primary={`Role ${p.role}: ${p.challenger} vs ${p.active}`} secondary={`p95 ${p.p95_c?.toFixed?.(3)}s vs ${p.p95_a?.toFixed?.(3)}s; cost ${p.cost_c?.toFixed?.(6)} vs ${p.cost_a?.toFixed?.(6)}`} />
                    </ListItem>
                  ))}
                </List>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6">Approval Queue</Typography>
            <List>
              {approvals.map((a) => (
                <ListItem key={a.id}
                  secondaryAction={
                    <Box>
                      <IconButton color="success" onClick={async () => { await approveProposal(a.id); setApprovals(await getApprovals()); }}>
                        <CheckIcon />
                      </IconButton>
                      <IconButton color="error" onClick={async () => { await denyProposal(a.id); setApprovals(await getApprovals()); }}>
                        <CloseIcon />
                      </IconButton>
                    </Box>
                  }
                >
                  <ListItemText primary={a.content} />
                </ListItem>
              ))}
              {approvals.length === 0 && <Typography variant="body2" color="text.secondary">No pending approvals.</Typography>}
            </List>
          </Paper>
        </Grid>
      </Grid>

      {/* Swarm + Router section */}
      <Grid container spacing={2} sx={{ mt: 2 }}>
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Stack direction="row" justifyContent="space-between" alignItems="center">
              <Typography variant="h6">Swarm Status</Typography>
              <Button size="small" variant="outlined" onClick={async () => { try { setSwarm(await getSwarmStatus()); } catch {} }}>Refresh</Button>
            </Stack>
            <Typography variant="body2" sx={{ mt: 1 }}>
              {swarm ? `Enabled: ${String(swarm.swarm_enabled)} • Nodes: ${swarm.active_nodes ?? 0}` : 'No swarm info'}
            </Typography>
            {swarm?.nodes && (
              <Typography variant="caption" sx={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(swarm.nodes, null, 2)}</Typography>
            )}
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper variant="outlined" sx={{ p: 2 }}>
            <Typography variant="h6">Router Thresholds</Typography>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
              <TextField size="small" label="Conf" value={confThreshold} onChange={e => setConfThreshold(e.target.value)} sx={{ width: 120 }} />
              <TextField size="small" label="Support" value={supportThreshold} onChange={e => setSupportThreshold(e.target.value)} sx={{ width: 120 }} />
              <TextField size="small" label="Max CoT" value={maxCot} onChange={e => setMaxCot(e.target.value)} sx={{ width: 120 }} />
            </Stack>
            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1} sx={{ mt: 1 }}>
              <TextField size="small" label="Admin Token" value={adminToken} onChange={e => setAdminToken(e.target.value)} sx={{ minWidth: 220 }} />
              <Button size="small" variant="outlined" onClick={onApplyThresholds}>Apply</Button>
            </Stack>
            <Typography variant="caption" color="text.secondary">Requires ADMIN_TOKEN configured on server.</Typography>
          </Paper>
        </Grid>
      </Grid>

      {snack.map((s, idx) => (
        <Snackbar key={idx} open={s.open} autoHideDuration={6000} onClose={() => setSnack(prev => prev.filter((_, i) => i !== idx))}>
          <Alert onClose={() => setSnack(prev => prev.filter((_, i) => i !== idx))} severity="info" sx={{ width: '100%' }}>
            {s.msg}
          </Alert>
        </Snackbar>
      ))}
    </>
  );
};

export default SystemPanel;