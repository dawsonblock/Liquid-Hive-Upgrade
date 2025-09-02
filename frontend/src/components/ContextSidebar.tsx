import React from 'react';
import { Paper, Typography, List, ListItem, ListItemText, Divider } from '@mui/material';

type Props = { context?: string; reasoning?: string; intent?: string; rationale?: string };

const ContextSidebar: React.FC<Props> = ({ context, reasoning, intent, rationale }) => {
  const docs = (context || '').split(/\n\n\[\d+\]/).filter(Boolean);
  return (
    <Paper variant="outlined" sx={{ p: 2.5, borderRadius: 4 }}>
      <Typography variant="overline" sx={{ letterSpacing: 1.2 }}>Context</Typography>
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 1 }}>Awareness</Typography>
      <Typography variant="subtitle2" sx={{ mt: 1 }}>Operator Intent</Typography>
      <Typography variant="body2" color="text.secondary">{intent || 'Unknown'}</Typography>
      <Typography variant="subtitle2" sx={{ mt: 2 }}>Reasoning Strategy</Typography>
      <Typography variant="body2" color="text.secondary">{reasoning || 'N/A'}</Typography>
      {rationale && (<>
        <Typography variant="subtitle2" sx={{ mt: 2 }}>Decision Rationale</Typography>
        <Typography variant="body2" color="text.secondary">{rationale}</Typography>
      </>)}
      <Divider sx={{ my: 2 }} />
      <Typography variant="subtitle2">RAG Context</Typography>
      <List dense>
        {docs.length === 0 && <Typography variant="body2" color="text.secondary">No documents.</Typography>}
        {docs.map((d, i) => (
          <ListItem key={i}>
            <ListItemText primary={d.trim().slice(0, 120) + (d.length > 120 ? '…' : '')} />
          </ListItem>
        ))}
      </List>
    </Paper>
  );
};

export default ContextSidebar;