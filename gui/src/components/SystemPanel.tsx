import React, { useEffect, useState } from 'react';
import { Box, Card, CardContent, Typography, Grid, Button } from '@mui/material';

interface SystemState {
  uptime_s: number;
  memory_size: number;
  graph: { nodes: number; edges: number };
  self_awareness_metrics: { phi: number; glyphs: string[] };
}

interface Approval {
  id: number;
  content: string;
}

export default function SystemPanel() {
  const [state, setState] = useState<SystemState | null>(null);
  const [approvals, setApprovals] = useState<Approval[]>([]);

  const loadState = async () => {
    try {
      const resp = await fetch('/state');
      const data = await resp.json();
      setState(data as SystemState);
    } catch (e) {}
  };
  const loadApprovals = async () => {
    try {
      const resp = await fetch('/approvals');
      const arr = await resp.json();
      setApprovals(arr);
    } catch (e) {}
  };
  useEffect(() => {
    loadState();
    loadApprovals();
    const timer = setInterval(() => {
      loadState();
      loadApprovals();
    }, 10000);
    return () => clearInterval(timer);
  }, []);
  const approve = async (id: number) => {
    await fetch(`/approvals/${id}/approve`, { method: 'POST' });
    loadApprovals();
  };
  const deny = async (id: number) => {
    await fetch(`/approvals/${id}/deny`, { method: 'POST' });
    loadApprovals();
  };
  return (
    <Box>
      <Grid container spacing={2} sx={{ mb: 2 }}>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2">Uptime</Typography>
              <Typography variant="h5">{state?.uptime_s ?? '--'} s</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2">Memory Size</Typography>
              <Typography variant="h5">{state?.memory_size ?? '--'}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2">Nodes</Typography>
              <Typography variant="h5">{state?.graph.nodes ?? '--'}</Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={3}>
          <Card>
            <CardContent>
              <Typography variant="subtitle2">Edges</Typography>
              <Typography variant="h5">{state?.graph.edges ?? '--'}</Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="subtitle2">Self-Awareness (Φ)</Typography>
          <Typography variant="h4">{state?.self_awareness_metrics?.phi?.toFixed(4) ?? '--'}</Typography>
          <Typography variant="h6">{state?.self_awareness_metrics?.glyphs?.join(' ') ?? ''}</Typography>
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Approval Queue</Typography>
          {approvals.length === 0 && <Typography variant="body2">No pending approvals.</Typography>}
          {approvals.map((item) => (
            <Box key={item.id} sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
              <Typography variant="body2" sx={{ flex: 1 }}>{item.content}</Typography>
              <Box sx={{ flexShrink: 0 }}>
                <Button size="small" variant="contained" color="success" onClick={() => approve(item.id)} sx={{ mr: 1 }}>Approve</Button>
                <Button size="small" variant="contained" color="error" onClick={() => deny(item.id)}>Deny</Button>
              </Box>
            </Box>
          ))}
        </CardContent>
      </Card>
    </Box>
  );
}