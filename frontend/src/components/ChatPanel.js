import { jsx as _jsx, jsxs as _jsxs, Fragment as _Fragment } from 'react/jsx-runtime';
import { useEffect, useRef, useState } from 'react';
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
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ReplayIcon from '@mui/icons-material/Replay';
import CheckIcon from '@mui/icons-material/Check';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SendIcon from '@mui/icons-material/Send';
import AttachFileIcon from '@mui/icons-material/AttachFile';
import Markdown from './Markdown';
import { postChat, postVision, fetchState } from '../services/api';
import { useDispatch, useSelector } from 'react-redux';
import { addChat } from '../store';
import ContextSidebar from './ContextSidebar';
const ChatPanel = () => {
  const [input, setInput] = useState('');
  const [imageFile, setImageFile] = useState(null);
  const [groundingRequired, setGroundingRequired] = useState(false);
  const [lastContext, setLastContext] = useState();
  const [lastReasoning, setLastReasoning] = useState();
  const [lastIntent, setLastIntent] = useState();
  const [lastRationale, setLastRationale] = useState();
  const [lastCritique, setLastCritique] = useState();
  const [lastCorrection, setLastCorrection] = useState();
  const dispatch = useDispatch();
  const history = useSelector(s => s.chatHistory);
  const listRef = useRef(null);
  const [copiedIdx, setCopiedIdx] = useState(null);
  const findPrevUserPrompt = fromIndex => {
    for (let j = fromIndex - 1; j >= 0; j--) {
      const msg = history[j];
      if (msg?.role === 'user') return msg.content;
    }
    return null;
  };
  const handleCopy = async (text, idx) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(c => (c === idx ? null : c)), 1500);
    } catch {}
  };
  const handleRegenerate = async idx => {
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
      if (typeof el.scrollTo === 'function') {
        el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
      } else {
        el.scrollTop = el.scrollHeight;
      }
    }
  }, [history.length]);
  return _jsxs(Grid, {
    container: true,
    spacing: 3,
    children: [
      _jsx(Grid, {
        item: true,
        xs: 12,
        md: 8,
        children: _jsxs(Stack, {
          spacing: 2,
          sx: { height: { xs: 'auto', md: 'calc(100vh - 140px)' } },
          children: [
            _jsxs(Paper, {
              variant: 'outlined',
              sx: {
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
              },
              ref: listRef,
              children: [
                history.length === 0 &&
                  _jsxs(Box, {
                    sx: { textAlign: 'center', color: 'text.secondary', mt: 8 },
                    children: [
                      _jsxs(Typography, {
                        variant: 'h5',
                        gutterBottom: true,
                        sx: { fontWeight: 700 },
                        children: [
                          'Welcome to ',
                          _jsx(Box, {
                            component: 'span',
                            sx: { color: 'primary.main' },
                            children: 'LIQUID\u2011HIVE',
                          }),
                        ],
                      }),
                      _jsx(Typography, {
                        variant: 'body2',
                        children: 'Ask anything. Press Enter to send, Shift+Enter for a new line.',
                      }),
                      _jsxs(Stack, {
                        direction: 'row',
                        spacing: 1,
                        justifyContent: 'center',
                        sx: { mt: 2 },
                        children: [
                          _jsx(Chip, {
                            size: 'small',
                            label: 'Chat',
                            color: 'primary',
                            variant: 'outlined',
                          }),
                          _jsx(Chip, {
                            size: 'small',
                            label: 'Vision',
                            color: 'secondary',
                            variant: 'outlined',
                          }),
                          _jsx(Chip, { size: 'small', label: 'RAG', variant: 'outlined' }),
                        ],
                      }),
                    ],
                  }),
                history.map((m, i) => {
                  const isUser = m.role === 'user';
                  return _jsxs(
                    Stack,
                    {
                      direction: 'row',
                      spacing: 1.5,
                      sx: {
                        mb: 2,
                        alignItems: 'flex-start',
                        opacity: 0,
                        animation: 'fadeIn 200ms ease forwards',
                      },
                      children: [
                        _jsx(Avatar, {
                          sx: {
                            width: 28,
                            height: 28,
                            mt: 0.25,
                            bgcolor: isUser ? 'primary.main' : 'secondary.main',
                            color: 'primary.contrastText',
                          },
                          children: isUser ? 'U' : 'A',
                        }),
                        _jsxs(Box, {
                          sx: {
                            maxWidth: '100%',
                            flex: 1,
                            '& .markdown': {
                              wordBreak: 'break-word',
                              lineHeight: 1.6,
                            },
                          },
                          children: [
                            _jsxs(Box, {
                              sx: {
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
                              },
                              children: [
                                _jsxs(Stack, {
                                  direction: 'row',
                                  spacing: 1,
                                  alignItems: 'center',
                                  sx: { mb: 0.5 },
                                  children: [
                                    _jsx(Typography, {
                                      variant: 'caption',
                                      color: 'text.secondary',
                                      children: isUser ? 'You' : 'Assistant',
                                    }),
                                    m.timestamp &&
                                      _jsx(Tooltip, {
                                        title: new Date(m.timestamp).toLocaleString(),
                                        children: _jsx(Typography, {
                                          variant: 'caption',
                                          color: 'text.disabled',
                                          children: new Date(m.timestamp).toLocaleTimeString([], {
                                            hour: '2-digit',
                                            minute: '2-digit',
                                          }),
                                        }),
                                      }),
                                  ],
                                }),
                                _jsx(Box, {
                                  className: 'markdown',
                                  children: _jsx(Markdown, { children: m.content }),
                                }),
                              ],
                            }),
                            !isUser &&
                              _jsxs(Stack, {
                                direction: 'row',
                                spacing: 1,
                                sx: { mt: 0.5 },
                                children: [
                                  _jsx(Tooltip, {
                                    title: copiedIdx === i ? 'Copied' : 'Copy message',
                                    children: _jsx('span', {
                                      children: _jsx(IconButton, {
                                        size: 'small',
                                        onClick: () => handleCopy(m.content, i),
                                        'aria-label': 'Copy message',
                                        children:
                                          copiedIdx === i
                                            ? _jsx(CheckIcon, { fontSize: 'small' })
                                            : _jsx(ContentCopyIcon, { fontSize: 'small' }),
                                      }),
                                    }),
                                  }),
                                  _jsx(Tooltip, {
                                    title: 'Regenerate response',
                                    children: _jsx('span', {
                                      children: _jsx(IconButton, {
                                        size: 'small',
                                        onClick: () => handleRegenerate(i),
                                        'aria-label': 'Regenerate response',
                                        children: _jsx(ReplayIcon, { fontSize: 'small' }),
                                      }),
                                    }),
                                  }),
                                ],
                              }),
                            (lastCritique || lastCorrection) &&
                              !isUser &&
                              _jsxs(Accordion, {
                                sx: { mt: 1 },
                                children: [
                                  _jsx(AccordionSummary, {
                                    expandIcon: _jsx(ExpandMoreIcon, {}),
                                    children: _jsx(Typography, {
                                      variant: 'caption',
                                      children: 'Show Reasoning',
                                    }),
                                  }),
                                  _jsxs(AccordionDetails, {
                                    children: [
                                      lastCritique &&
                                        _jsxs(_Fragment, {
                                          children: [
                                            _jsx(Typography, {
                                              variant: 'subtitle2',
                                              children: 'Judge Critique',
                                            }),
                                            _jsx(Typography, {
                                              variant: 'body2',
                                              color: 'text.secondary',
                                              children: lastCritique,
                                            }),
                                          ],
                                        }),
                                      lastCorrection &&
                                        _jsxs(_Fragment, {
                                          children: [
                                            _jsx(Typography, {
                                              variant: 'subtitle2',
                                              sx: { mt: 1 },
                                              children: 'Correction Analysis',
                                            }),
                                            _jsx(Typography, {
                                              variant: 'body2',
                                              color: 'text.secondary',
                                              children: lastCorrection,
                                            }),
                                          ],
                                        }),
                                    ],
                                  }),
                                ],
                              }),
                          ],
                        }),
                      ],
                    },
                    i
                  );
                }),
              ],
            }),
            _jsxs(Paper, {
              variant: 'outlined',
              sx: { p: 1, borderRadius: 999, px: 1.5 },
              children: [
                _jsxs(Stack, {
                  direction: 'row',
                  spacing: 1,
                  alignItems: 'center',
                  children: [
                    _jsx(TextField, {
                      fullWidth: true,
                      size: 'small',
                      placeholder: 'Type a message...',
                      value: input,
                      onChange: e => setInput(e.target.value),
                      multiline: true,
                      minRows: 1,
                      maxRows: 6,
                      onKeyDown: e => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          sendText();
                        }
                      },
                    }),
                    _jsxs(IconButton, {
                      component: 'label',
                      color: imageFile ? 'secondary' : 'default',
                      children: [
                        _jsx(AttachFileIcon, {}),
                        _jsx('input', {
                          'aria-label': 'Attach file',
                          type: 'file',
                          hidden: true,
                          accept: 'image/*',
                          onChange: e => setImageFile(e.target.files?.[0] || null),
                        }),
                      ],
                    }),
                    _jsx(IconButton, {
                      color: 'primary',
                      onClick: sendText,
                      'aria-label': 'Send message',
                      children: _jsx(SendIcon, {}),
                    }),
                    _jsx(Button, {
                      variant: 'outlined',
                      onClick: sendVision,
                      disabled: !imageFile,
                      children: 'Send Image',
                    }),
                  ],
                }),
                _jsx(FormControlLabel, {
                  sx: { ml: 0.5, mt: 0.5 },
                  control: _jsx(Switch, {
                    checked: groundingRequired,
                    onChange: e => setGroundingRequired(e.target.checked),
                  }),
                  label: 'Grounding Required',
                }),
              ],
            }),
          ],
        }),
      }),
      _jsx(Grid, {
        item: true,
        xs: 12,
        md: 4,
        children: _jsx(ContextSidebar, {
          context: lastContext,
          reasoning: lastReasoning,
          intent: lastIntent,
          rationale: lastRationale,
        }),
      }),
    ],
  });
};
export default ChatPanel;
//# sourceMappingURL=ChatPanel.js.map
