import React, { useState } from 'react';
import { Box, Paper, TextField, IconButton, Stack, Typography, Button, Switch, FormControlLabel } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import ReactMarkdown from 'react-markdown';
import { postChat, postVision, fetchState } from '@services/api';
import { useDispatch, useSelector } from 'react-redux';
import type { RootState } from '../store';
import { addChat } from '../store';

const ChatPanel: React.FC = () => {
  const [input, setInput] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [groundingRequired, setGroundingRequired] = useState(false);
  const dispatch = useDispatch();
  const history = useSelector((s: RootState) => s.chatHistory);

  const sendText = async () => {
    if (!input.trim()) return;
    dispatch(addChat({ role: 'user', content: input }));
    const res = await postChat(input);
    dispatch(addChat({ role: 'assistant', content: res.answer }));
    try { await fetchState(); } catch {}
    setInput('');
  };

  const sendVision = async () => {
    if (!imageFile) return;
    const form = new FormData();
    form.append('file', imageFile);
    form.append('question', input || 'What is in this image?');
    const res = await postVision(form, groundingRequired);
    dispatch(addChat({ role: 'assistant', content: res.answer }));
    try { await fetchState(); } catch {}
  };

  return (
    <Stack spacing={2}>
      <Paper variant="outlined" sx={{ p: 2, height: 500, overflowY: 'auto', bgcolor: 'background.default' }}>
        {history.length === 0 && (
          <Typography variant="body2" color="text.secondary">Start the conversation with the Cognitive Core. Attach an image to ask visual questions.</Typography>
        )}
        {history.map((m, i) => (
          <Box key={i} sx={{ mb: 2 }}>
            <Typography variant="caption" color="text.secondary">{m.role.toUpperCase()}</Typography>
            <ReactMarkdown>{m.content}</ReactMarkdown>
          </Box>
        ))}
      </Paper>
      <Stack direction="row" spacing={1} alignItems="center">
        <TextField fullWidth size="small" placeholder="Type a message..." value={input} onChange={e => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendText(); } }} />
        <IconButton component="label" color={imageFile ? 'secondary' : 'default'}>
          <AttachFileIcon />
          <input type="file" hidden accept="image/*" onChange={e => setImageFile(e.target.files?.[0] || null)} />
        </IconButton>
        <IconButton color="primary" onClick={sendText}><SendIcon /></IconButton>
        <Button variant="outlined" onClick={sendVision} disabled={!imageFile}>Send Image</Button>
      </Stack>
      <FormControlLabel control={<Switch checked={groundingRequired} onChange={e => setGroundingRequired(e.target.checked)} />} label="Grounding Required" />
    </Stack>
  );
};

export default ChatPanel;