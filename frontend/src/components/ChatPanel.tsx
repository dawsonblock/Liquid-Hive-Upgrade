import AttachFileIcon from '@mui/icons-material/AttachFile';
import CheckIcon from '@mui/icons-material/Check';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ReplayIcon from '@mui/icons-material/Replay';
import SendIcon from '@mui/icons-material/Send';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Stack,
  Typography,
  Button,
  Switch,
  FormControlLabel,
  Grid,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Avatar,
  Chip,
  Tooltip,
} from '@mui/material';
import React, { useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';

import { postChat, postVision, fetchState } from '../services/api';
import type { RootState } from '../store';
import { addChat } from '../store';

import ContextSidebar from './ContextSidebar';
import Markdown from './Markdown';

const ChatPanel: React.FC = () => {
  const [input, setInput] = useState('');
  const [imageFile, setImageFile] = useState<File | null>(null);
  const [groundingRequired, setGroundingRequired] = useState(false);
  const [lastContext, setLastContext] = useState<string | undefined>();
  const [lastReasoning, setLastReasoning] = useState<string | undefined>();
  const [lastIntent, setLastIntent] = useState<string | undefined>();
  const [lastRationale, setLastRationale] = useState<string | undefined>();
  const [lastCritique, setLastCritique] = useState<string | undefined>();
  const [lastCorrection, setLastCorrection] = useState<string | undefined>();
  const dispatch = useDispatch();
  const history = useSelector((s: RootState) => s.chatHistory);
  const listRef = useRef<HTMLDivElement | null>(null);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

  const findPrevUserPrompt = (fromIndex: number) => {
    for (let j = fromIndex - 1; j >= 0; j--) {
      const msg = (history as any)[j];
      if (msg?.role === 'user') return msg.content as string;
    }
    return null;
  };

  const handleCopy = async (text: string, idx: number) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(c => (c === idx ? null : c)), 1500);
    } catch {}
  };

  const handleRegenerate = async (idx: number) => {
    const prompt = findPrevUserPrompt(idx);
    if (!prompt) return;
    const res = await postChat(prompt);
    dispatch(addChat({ role: 'assistant', content: res.answer }));
    setLastContext(res.context);
    setLastReasoning(res.reasoning_strategy);
    setLastRationale(res.selector_reason);
    try {
      const st = await fetchState();
      setLastIntent(st?.operator_intent);
    } catch {}
  };

  const sendText = async () => {
    if (!input.trim()) return;
    dispatch(addChat({ role: 'user', content: input }));
    const res = await postChat(input);
    dispatch(addChat({ role: 'assistant', content: res.answer }));
    setLastContext(res.context);
    setLastReasoning(res.reasoning_strategy);
    setLastRationale(res.selector_reason);
    try {
      const st = await fetchState();
      setLastIntent(st?.operator_intent);
    } catch {}
    setInput('');
  };

  const sendVision = async () => {
    if (!imageFile) return;
    const form = new FormData();
    form.append('file', imageFile);
    form.append('question', input || 'What is in this image?');
    const res = await postVision(form, groundingRequired);
    dispatch(addChat({ role: 'assistant', content: res.answer }));
    setLastCritique(res.critique);
    try {
      const st = await fetchState();
      setLastIntent(st?.operator_intent);
    } catch {}
  };

  useEffect(() => {
    // Auto-scroll to bottom on new messages
    const el = listRef.current;
    if (el) {
      if (typeof (el as any).scrollTo === 'function') {
        (el as any).scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
      } else {
        el.scrollTop = el.scrollHeight;
      }
    }
  }, [history.length]);

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={8}>
        <Stack spacing={2} sx={{ height: { xs: 'auto', md: 'calc(100vh - 140px)' } }}>
          <Paper
            variant='outlined'
            sx={{
              p: { xs: 2, md: 3 },
              flex: 1,
              minHeight: 360,
              overflowY: 'auto',
              bgcolor: t =>
                t.palette.mode === 'dark' ? 'rgba(2,6,23,0.6)' : 'rgba(255,255,255,0.9)',
              borderRadius: 4,
              backgroundImage: t =>
                t.palette.mode === 'dark'
                  ? 'radial-gradient(600px 300px at 10% -10%, rgba(26,115,232,0.10), transparent)'
                  : 'radial-gradient(600px 300px at 10% -10%, rgba(26,115,232,0.06), transparent)',
            }}
            ref={listRef}
          >
            {history.length === 0 && (
              <Box sx={{ textAlign: 'center', color: 'text.secondary', mt: 8 }}>
                <Typography variant='h5' gutterBottom sx={{ fontWeight: 700 }}>
                  Welcome to{' '}
                  <Box component='span' sx={{ color: 'primary.main' }}>
                    LIQUID‑HIVE
                  </Box>
                </Typography>
                <Typography variant='body2'>
                  Ask anything. Press Enter to send, Shift+Enter for a new line.
                </Typography>
                <Stack direction='row' spacing={1} justifyContent='center' sx={{ mt: 2 }}>
                  <Chip size='small' label='Chat' color='primary' variant='outlined' />
                  <Chip size='small' label='Vision' color='secondary' variant='outlined' />
                  <Chip size='small' label='RAG' variant='outlined' />
                </Stack>
              </Box>
            )}

            {history.map((m, i) => {
              const isUser = m.role === 'user';
              return (
                <Stack
                  key={i}
                  direction='row'
                  spacing={1.5}
                  sx={{
                    mb: 2,
                    alignItems: 'flex-start',
                    opacity: 0,
                    animation: 'fadeIn 200ms ease forwards',
                  }}
                >
                  <Avatar
                    sx={{
                      width: 28,
                      height: 28,
                      mt: 0.25,
                      bgcolor: isUser ? 'primary.main' : 'secondary.main',
                      color: 'primary.contrastText',
                    }}
                  >
                    {isUser ? 'U' : 'A'}
                  </Avatar>
                  <Box
                    sx={{
                      maxWidth: '100%',
                      flex: 1,
                      '& .markdown': {
                        wordBreak: 'break-word',
                        lineHeight: 1.6,
                      },
                    }}
                  >
                    <Box
                      sx={{
                        display: 'inline-block',
                        px: 1.75,
                        py: 1.25,
                        borderRadius: 3,
                        bgcolor: t =>
                          isUser
                            ? t.palette.mode === 'dark'
                              ? 'rgba(26,115,232,0.14)'
                              : 'rgba(26,115,232,0.08)'
                            : t.palette.background.paper,
                        border: t => `1px solid ${t.palette.divider}`,
                        boxShadow: t =>
                          t.palette.mode === 'dark' ? 'none' : '0 1px 3px rgba(0,0,0,0.06)',
                      }}
                    >
                      <Stack direction='row' spacing={1} alignItems='center' sx={{ mb: 0.5 }}>
                        <Typography variant='caption' color='text.secondary'>
                          {isUser ? 'You' : 'Assistant'}
                        </Typography>
                        {m.timestamp && (
                          <Tooltip title={new Date(m.timestamp).toLocaleString()}>
                            <Typography variant='caption' color='text.disabled'>
                              {new Date(m.timestamp).toLocaleTimeString([], {
                                hour: '2-digit',
                                minute: '2-digit',
                              })}
                            </Typography>
                          </Tooltip>
                        )}
                      </Stack>
                      <Box className='markdown'>
                        <Markdown>{m.content}</Markdown>
                      </Box>
                    </Box>

                    {!isUser && (
                      <Stack direction='row' spacing={1} sx={{ mt: 0.5 }}>
                        <Tooltip title={copiedIdx === i ? 'Copied' : 'Copy message'}>
                          <span>
                            <IconButton
                              size='small'
                              onClick={() => handleCopy(m.content, i)}
                              aria-label='Copy message'
                            >
                              {copiedIdx === i ? (
                                <CheckIcon fontSize='small' />
                              ) : (
                                <ContentCopyIcon fontSize='small' />
                              )}
                            </IconButton>
                          </span>
                        </Tooltip>
                        <Tooltip title='Regenerate response'>
                          <span>
                            <IconButton
                              size='small'
                              onClick={() => handleRegenerate(i)}
                              aria-label='Regenerate response'
                            >
                              <ReplayIcon fontSize='small' />
                            </IconButton>
                          </span>
                        </Tooltip>
                      </Stack>
                    )}

                    {(lastCritique || lastCorrection) && !isUser && (
                      <Accordion sx={{ mt: 1 }}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant='caption'>Show Reasoning</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          {lastCritique && (
                            <>
                              <Typography variant='subtitle2'>Judge Critique</Typography>
                              <Typography variant='body2' color='text.secondary'>
                                {lastCritique}
                              </Typography>
                            </>
                          )}
                          {lastCorrection && (
                            <>
                              <Typography variant='subtitle2' sx={{ mt: 1 }}>
                                Correction Analysis
                              </Typography>
                              <Typography variant='body2' color='text.secondary'>
                                {lastCorrection}
                              </Typography>
                            </>
                          )}
                        </AccordionDetails>
                      </Accordion>
                    )}
                  </Box>
                </Stack>
              );
            })}
          </Paper>

          <Paper variant='outlined' sx={{ p: 1, borderRadius: 999, px: 1.5 }}>
            <Stack direction='row' spacing={1} alignItems='center'>
              <TextField
                fullWidth
                size='small'
                placeholder='Type a message...'
                value={input}
                onChange={e => setInput(e.target.value)}
                multiline
                minRows={1}
                maxRows={6}
                onKeyDown={e => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    sendText();
                  }
                }}
              />
              <IconButton component='label' color={imageFile ? 'secondary' : 'default'}>
                <AttachFileIcon />
                <input
                  aria-label='Attach file'
                  type='file'
                  hidden
                  accept='image/*'
                  onChange={e => setImageFile(e.target.files?.[0] || null)}
                />
              </IconButton>
              <IconButton color='primary' onClick={sendText} aria-label='Send message'>
                <SendIcon />
              </IconButton>
              <Button variant='outlined' onClick={sendVision} disabled={!imageFile}>
                Send Image
              </Button>
            </Stack>
            <FormControlLabel
              sx={{ ml: 0.5, mt: 0.5 }}
              control={
                <Switch
                  checked={groundingRequired}
                  onChange={e => setGroundingRequired(e.target.checked)}
                />
              }
              label='Grounding Required'
            />
          </Paper>
        </Stack>
      </Grid>
      <Grid item xs={12} md={4}>
        <ContextSidebar
          context={lastContext}
          reasoning={lastReasoning}
          intent={lastIntent}
          rationale={lastRationale}
        />
      </Grid>
    </Grid>
  );
};

export default ChatPanel;
