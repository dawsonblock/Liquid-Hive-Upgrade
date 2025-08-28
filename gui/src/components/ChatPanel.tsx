import React, { useState } from 'react';
import { Box, Button, Checkbox, FormControlLabel, Paper, TextField, Typography, Divider } from '@mui/material';

interface Message {
  sender: 'user' | 'assistant';
  content: string;
}

export default function ChatPanel() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [grounding, setGrounding] = useState(false);

  const sendMessage = async () => {
    if (!input && !file) return;
    const userMsg: Message = { sender: 'user', content: input || (file ? `[Attached: ${file.name}]` : '') };
    setMessages((msgs) => [...msgs, userMsg]);
    try {
      if (file) {
        const form = new FormData();
        form.append('question', input || '');
        form.append('file', file);
        const url = `/vision${grounding ? '?grounding_required=true' : ''}`;
        const resp = await fetch(url, { method: 'POST', body: form });
        const data = await resp.json();
        setMessages((msgs) => [...msgs, { sender: 'assistant', content: data.answer || JSON.stringify(data) }]);
      } else {
        const resp = await fetch('/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ q: input }) });
        const data = await resp.json();
        setMessages((msgs) => [...msgs, { sender: 'assistant', content: data.answer || JSON.stringify(data) }]);
      }
    } catch (err) {
      setMessages((msgs) => [...msgs, { sender: 'assistant', content: 'Error sending message' }]);
    }
    setInput('');
    setFile(null);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'row', gap: 2 }}>
      <Box sx={{ flex: 2, display: 'flex', flexDirection: 'column' }}>
        <Paper sx={{ flex: 1, p: 2, overflowY: 'auto', mb: 2 }}>
          {messages.map((msg, idx) => (
            <Box key={idx} sx={{ textAlign: msg.sender === 'user' ? 'right' : 'left', mb: 1 }}>
              <Typography variant="body2" sx={{ fontWeight: msg.sender === 'user' ? 'bold' : 'normal' }}>{msg.content}</Typography>
            </Box>
          ))}
        </Paper>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
          {file && <Typography variant="caption">Selected: {file.name}</Typography>}
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button component="label" variant="outlined">Attach File
              <input type="file" hidden onChange={(e) => setFile(e.target.files ? e.target.files[0] : null)} />
            </Button>
            <TextField
              fullWidth
              multiline
              maxRows={4}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Type your message..."
            />
            <Button variant="contained" onClick={sendMessage}>Send</Button>
          </Box>
          <FormControlLabel
            control={<Checkbox checked={grounding} onChange={() => setGrounding(!grounding)} />}
            label="Grounding Required"
          />
        </Box>
      </Box>
      <Divider orientation="vertical" flexItem />
      <Box sx={{ flex: 1, p: 2 }}>
        <Typography variant="h6">Context Awareness</Typography>
        <Typography variant="subtitle2">Operator Intent:</Typography>
        <Typography variant="body2" sx={{ mb: 1 }}>-- Not loaded --</Typography>
        <Typography variant="subtitle2">RAG Context:</Typography>
        <Typography variant="body2" sx={{ mb: 1 }}>-- Not loaded --</Typography>
        <Typography variant="subtitle2">Reasoning Strategy:</Typography>
        <Typography variant="body2">-- Not loaded --</Typography>
      </Box>
    </Box>
  );
}