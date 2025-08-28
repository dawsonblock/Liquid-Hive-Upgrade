import React, { useState, useEffect } from 'react';
import { Box, Card, CardContent, Typography, Button, Grid, Switch, FormControlLabel, TextField } from '@mui/material';

interface AdapterRow {
  role: string;
  champion: string;
  challenger?: string;
}

export default function ForgePanel() {
  const [trainingStatus, setTrainingStatus] = useState('Idle');
  const [adapterTable, setAdapterTable] = useState<AdapterRow[]>([]);
  const [enableOracle, setEnableOracle] = useState(true);
  const [forceGpt4o, setForceGpt4o] = useState(false);
  const [lastAdapter, setLastAdapter] = useState('');

  const loadAdapters = async () => {
    try {
      const resp = await fetch('/adapters');
      const data = await resp.json();
      setAdapterTable(data);
    } catch (e) {}
  };
  useEffect(() => {
    loadAdapters();
  }, []);
  const igniteTraining = async () => {
    setTrainingStatus('Building Dataset');
    try {
      const resp = await fetch('/train', { method: 'POST' });
      const data = await resp.json();
      setTrainingStatus('Complete');
      setLastAdapter(data.adapter_path || '');
      loadAdapters();
    } catch (e) {
      setTrainingStatus('Error');
    }
  };
  const promote = async (role: string) => {
    await fetch(`/adapters/promote/${role}`, { method: 'POST' });
    loadAdapters();
  };
  const updateGovernor = async (enabled: boolean, force: boolean) => {
    await fetch('/config/governor', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ ENABLE_ORACLE_REFINEMENT: enabled, FORCE_GPT4O_ARBITER: force }) });
  };
  const handleToggleOracle = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setEnableOracle(e.target.checked);
    updateGovernor(e.target.checked, forceGpt4o);
  };
  const handleToggleForce = async (e: React.ChangeEvent<HTMLInputElement>) => {
    setForceGpt4o(e.target.checked);
    updateGovernor(enableOracle, e.target.checked);
  };
  return (
    <Box>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ mb: 2 }}>Training Pipeline</Typography>
          <Button variant="contained" onClick={igniteTraining}>Ignite Training Cycle</Button>
          <Typography variant="body2" sx={{ mt: 1 }}>Status: {trainingStatus}</Typography>
          <Typography variant="body2">Last adapter: {lastAdapter || '--'}</Typography>
        </CardContent>
      </Card>
      <Card sx={{ mb: 2 }}>
        <CardContent>
          <Typography variant="h6">Adapter Deployment</Typography>
          <Grid container spacing={1} sx={{ mt: 1 }}>
            <Grid item xs={12} md={4}><strong>Role</strong></Grid>
            <Grid item xs={12} md={4}><strong>Champion</strong></Grid>
            <Grid item xs={12} md={4}><strong>Challenger</strong></Grid>
          </Grid>
          {adapterTable.map((row) => (
            <Grid container spacing={1} key={row.role} sx={{ mt: 0.5 }}>
              <Grid item xs={12} md={4}>{row.role}</Grid>
              <Grid item xs={12} md={4}>{row.champion}</Grid>
              <Grid item xs={12} md={3}>{row.challenger || '--'}</Grid>
              <Grid item xs={12} md={1}>{row.challenger && <Button size="small" variant="contained" onClick={() => promote(row.role)}>Promote</Button>}</Grid>
            </Grid>
          ))}
        </CardContent>
      </Card>
      <Card>
        <CardContent>
          <Typography variant="h6">Arbiter Governor</Typography>
          <FormControlLabel control={<Switch checked={enableOracle} onChange={handleToggleOracle} />} label="Enable Oracle Refinement" />
          <FormControlLabel control={<Switch checked={forceGpt4o} onChange={handleToggleForce} />} label="Force GPT-4o Arbiter" />
        </CardContent>
      </Card>
    </Box>
  );
}