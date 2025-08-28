import React, { useEffect, useMemo, useState } from 'react';
import { Box, Grid, Paper, Typography, List, ListItem, ListItemText, IconButton, Stack, Chip } from '@mui/material';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import { getApprovals, approveProposal, denyProposal, fetchState } from '@services/api';

const SystemPanel: React.FC = () => {
  const [approvals, setApprovals] = useState<{ id: number; content: string }[]>([]);
  const [stateSummary, setStateSummary] = useState<any>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setApprovals(await getApprovals());
        setStateSummary(await fetchState());
      } catch {}
    };
    load();

    const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.type === 'state_update') setStateSummary(msg.payload);
        if (msg.type === 'approvals_update') setApprovals(msg.payload);
      } catch {}
    };
    return () => ws.close();
  }, []);

  const vitals = useMemo(() => stateSummary?.self_awareness_metrics || {}, [stateSummary]);

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} md={6}>
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Typography variant="h6">Core Vitals & Self‑Awareness (Φ)</Typography>
          <Stack direction="row" spacing={2} sx={{ mt: 1 }}>
            <Chip label={`Phi: ${vitals.phi ?? 'N/A'}`} color="primary" />
            <Chip label={`Memories: ${stateSummary?.memory_size ?? 'N/A'}`} />
          </Stack>
          <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle2">Operator Intent</Typography>
            <Typography variant="body2" color="text.secondary">{stateSummary?.operator_intent ?? 'Unknown'}</Typography>
          </Box>
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
  );
};

export default SystemPanel;