import { jsx as _jsx, jsxs as _jsxs } from 'react/jsx-runtime';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CacheIcon from '@mui/icons-material/Memory';
import StreamIcon from '@mui/icons-material/PlayArrow';
import RefreshIcon from '@mui/icons-material/Refresh';
import StopIcon from '@mui/icons-material/Stop';
import SendIcon from '@mui/icons-material/Send';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ReplayIcon from '@mui/icons-material/Replay';
import CheckIcon from '@mui/icons-material/Check';
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  FormControlLabel,
  Grid,
  IconButton,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
  Tooltip,
} from '@mui/material';
import { useCallback, useEffect, useRef, useState } from 'react';
import Markdown from './Markdown';
import { useDispatch, useSelector } from 'react-redux';
import { useProviders } from '../contexts/ProvidersContext';
import { getBackendHttpBase, getBackendWsBase } from '../services/env';
import { addChat, updateLastMessage, finalizeStreamingMessage } from '../store';
import ContextSidebar from './ContextSidebar';
const StreamingChatPanel = () => {
  // State management
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState('disconnected');
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('');
  const [streamMetadata, setStreamMetadata] = useState(null);
  const [cacheAnalytics, setCacheAnalytics] = useState(null);
  const [cacheLoading, setCacheLoading] = useState(false);
  const { providers, loading: providersLoading, refresh: refreshProviders } = useProviders();
  // Context and metadata state
  const [lastContext, setLastContext] = useState();
  const [lastReasoning, setLastReasoning] = useState();
  const [lastIntent, setLastIntent] = useState();
  const [lastRationale, setLastRationale] = useState();
  // Redux
  const dispatch = useDispatch();
  const history = useSelector(s => s.chatHistory);
  // WebSocket reference
  const wsRef = useRef(null);
  const messagesEndRef = useRef(null);
  const [copiedIdx, setCopiedIdx] = useState(null);
  // providers controlled by context
  // Connect to WebSocket
  const connectWebSocket = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }
    setConnectionStatus('connecting');
    const wsBase = getBackendWsBase();
    const wsUrl = `${wsBase}/api/ws/chat`;
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      setConnectionStatus('connected');
      console.log('🔗 Connected to streaming chat WebSocket');
    };
    ws.onmessage = event => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };
    ws.onclose = () => {
      setConnectionStatus('disconnected');
      setIsStreaming(false);
      console.log('🔌 WebSocket connection closed');
    };
    ws.onerror = error => {
      setConnectionStatus('error');
      setIsStreaming(false);
      console.error('WebSocket error:', error);
    };
    wsRef.current = ws;
  }, []);
  // Handle WebSocket messages
  const handleWebSocketMessage = data => {
    switch (data.type) {
      case 'stream_start':
        setIsStreaming(true);
        setCurrentStreamingMessage('');
        setStreamMetadata(data.metadata);
        console.log('🚀 Stream started:', data.metadata);
        break;
      case 'chunk':
        setCurrentStreamingMessage(prev => prev + data.content);
        // Update the last assistant message in real-time
        if (history.length > 0 && history[history.length - 1].role === 'assistant') {
          dispatch(updateLastMessage(currentStreamingMessage + data.content));
        }
        break;
      case 'cached_response':
        // Handle cached response
        dispatch(
          addChat({
            role: 'assistant',
            content: data.content,
            timestamp: new Date(),
            cached: true,
            metadata: data.metadata,
          })
        );
        setStreamMetadata({ ...(data.metadata || {}), cached: true });
        break;
      case 'stream_complete':
        setIsStreaming(false);
        // Finalize the streaming message
        if (currentStreamingMessage) {
          // Update final message with complete content
          dispatch(updateLastMessage(currentStreamingMessage));
        }
        setCurrentStreamingMessage('');
        setStreamMetadata(null);
        console.log('✅ Stream completed:', data.metadata);
        break;
      case 'error':
        setIsStreaming(false);
        dispatch(
          addChat({
            role: 'assistant',
            content: `Error: ${data.error}`,
            timestamp: new Date(),
            metadata: { error: true },
          })
        );
        console.error('❌ Streaming error:', data.error);
        break;
      default:
        console.log('📨 Unknown message type:', data.type);
    }
  };
  const resendForRegeneration = useCallback(
    idx => {
      // Find the nearest previous user prompt and resend it
      for (let j = idx - 1; j >= 0; j--) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const msg = history[j];
        if (msg?.role === 'user') {
          const payload = { q: msg.content, stream: streamingEnabled };
          if (wsRef.current?.readyState === WebSocket.OPEN) {
            wsRef.current.send(JSON.stringify(payload));
            // Add placeholder for assistant response
            dispatch(
              addChat({ role: 'assistant', content: '', timestamp: new Date(), isStreaming: true })
            );
          }
          break;
        }
      }
    },
    [dispatch, history, streamingEnabled]
  );
  const copyToClipboard = async (text, idx) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIdx(idx);
      setTimeout(() => setCopiedIdx(c => (c === idx ? null : c)), 1500);
    } catch {}
  };
  // Cache analytics fetcher
  const refreshCacheAnalytics = useCallback(async () => {
    try {
      setCacheLoading(true);
      const base = getBackendHttpBase();
      if (!base) return;
      const res = await fetch(`${base}/api/cache/analytics`);
      if (!res.ok) return;
      const json = await res.json();
      setCacheAnalytics(json);
    } catch (e) {
      // ignore
    } finally {
      setCacheLoading(false);
    }
  }, []);
  // Send message via WebSocket
  const sendStreamingMessage = async () => {
    if (!input.trim() || isStreaming) return;
    // Ensure WebSocket connection
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      connectWebSocket();
      await new Promise(resolve => setTimeout(resolve, 1000)); // Wait for connection
    }
    if (wsRef.current?.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return;
    }
    // Add user message to history
    dispatch(
      addChat({
        role: 'user',
        content: input,
        timestamp: new Date(),
      })
    );
    // Add placeholder for assistant response
    dispatch(
      addChat({
        role: 'assistant',
        content: '',
        timestamp: new Date(),
        isStreaming: true,
      })
    );
    // Send query via WebSocket
    const message = {
      q: input,
      stream: streamingEnabled,
    };
    wsRef.current.send(JSON.stringify(message));
    setInput('');
  };
  // Stop the current generation (finalize with partial content)
  const stopGeneration = useCallback(() => {
    if (!isStreaming) return;
    try {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        // Best-effort stop signal; backend may ignore if unsupported
        wsRef.current.send(JSON.stringify({ type: 'stop' }));
      }
    } catch {
      // ignore
    }
    // Finalize current partial message
    if (currentStreamingMessage) {
      dispatch(
        finalizeStreamingMessage({ content: currentStreamingMessage, metadata: streamMetadata })
      );
    }
    setIsStreaming(false);
    setCurrentStreamingMessage('');
    setStreamMetadata(null);
  }, [currentStreamingMessage, dispatch, isStreaming, streamMetadata]);
  // Auto-scroll to bottom
  useEffect(() => {
    const el = messagesEndRef.current;
    if (el && typeof el.scrollIntoView === 'function') {
      try {
        el.scrollIntoView({ behavior: 'smooth' });
      } catch {}
    }
  }, [history, currentStreamingMessage]);
  // Connect on component mount
  useEffect(() => {
    if (streamingEnabled) {
      connectWebSocket();
    }
    // Providers are fetched via context
    // Light cache analytics poll (30s)
    refreshCacheAnalytics();
    const iv = setInterval(() => refreshCacheAnalytics(), 30000);
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      clearInterval(iv);
    };
  }, [streamingEnabled, connectWebSocket, refreshProviders, refreshCacheAnalytics]);
  // auto-refresh handled by context
  // Connection status indicator
  const getConnectionStatusColor = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'success';
      case 'connecting':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'default';
    }
  };
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
          children: [
            _jsx(Paper, {
              variant: 'outlined',
              sx: { p: 1.5, bgcolor: 'background.paper', borderRadius: 4 },
              children: _jsxs(Stack, {
                direction: 'row',
                spacing: 2,
                alignItems: 'center',
                children: [
                  _jsx(Chip, {
                    icon:
                      connectionStatus === 'connecting'
                        ? _jsx(CircularProgress, { size: 16 })
                        : _jsx(StreamIcon, {}),
                    label: `Streaming: ${connectionStatus}`,
                    color: getConnectionStatusColor(),
                    variant: 'outlined',
                    size: 'small',
                  }),
                  streamMetadata &&
                    _jsx(Chip, {
                      icon: _jsx(CacheIcon, {}),
                      label: streamMetadata.cached
                        ? `Cache Hit${typeof streamMetadata.cache_similarity === 'number' ? ` (${(streamMetadata.cache_similarity * 100).toFixed(0)}%)` : ''}`
                        : 'Live Generation',
                      color: streamMetadata.cached ? 'success' : 'primary',
                      variant: 'outlined',
                      size: 'small',
                    }),
                  cacheAnalytics &&
                    _jsx(Chip, {
                      icon: _jsx(CacheIcon, {}),
                      label: `Cache: ${Math.round((cacheAnalytics.hit_rate || 0) * 100)}%`,
                      color: (cacheAnalytics.hit_rate || 0) > 0.5 ? 'success' : 'default',
                      variant: 'outlined',
                      size: 'small',
                    }),
                  isStreaming &&
                    _jsx(Typography, {
                      variant: 'caption',
                      color: 'primary',
                      children: 'Generating response...',
                    }),
                  _jsx(Box, { sx: { flex: 1 } }),
                  isStreaming &&
                    _jsx(Button, {
                      size: 'small',
                      color: 'error',
                      variant: 'outlined',
                      onClick: stopGeneration,
                      startIcon: _jsx(StopIcon, {}),
                      children: 'Stop',
                    }),
                  _jsx(Button, {
                    size: 'small',
                    variant: 'outlined',
                    onClick: refreshProviders,
                    startIcon: providersLoading
                      ? _jsx(CircularProgress, { size: 14 })
                      : _jsx(RefreshIcon, {}),
                    children: 'Refresh Providers',
                  }),
                  _jsx(Button, {
                    size: 'small',
                    variant: 'outlined',
                    onClick: refreshCacheAnalytics,
                    startIcon: cacheLoading
                      ? _jsx(CircularProgress, { size: 14 })
                      : _jsx(CacheIcon, {}),
                    children: 'Cache Analytics',
                  }),
                ],
              }),
            }),
            providers &&
              Object.keys(providers).length > 0 &&
              _jsx(Paper, {
                variant: 'outlined',
                sx: { p: 1 },
                children: _jsx(Stack, {
                  direction: 'row',
                  spacing: 1,
                  alignItems: 'center',
                  flexWrap: 'wrap',
                  children: Object.entries(providers).map(([name, info]) =>
                    _jsx(
                      Chip,
                      {
                        size: 'small',
                        label: `${name}: ${info?.status || 'unknown'}`,
                        color:
                          info?.status === 'healthy'
                            ? 'success'
                            : info?.status
                              ? 'warning'
                              : 'default',
                      },
                      name
                    )
                  ),
                }),
              }),
            _jsxs(Paper, {
              variant: 'outlined',
              sx: {
                p: 2.5,
                height: 520,
                overflowY: 'auto',
                bgcolor: t =>
                  t.palette.mode === 'dark' ? 'rgba(2,6,23,0.6)' : 'rgba(255,255,255,0.9)',
                borderRadius: 4,
              },
              children: [
                history.length === 0 &&
                  _jsx(Typography, {
                    variant: 'body2',
                    color: 'text.secondary',
                    children:
                      'Start the conversation with the Enhanced Cognitive Core. Streaming is enabled for real-time responses.',
                  }),
                history.map((message, i) =>
                  _jsxs(
                    Box,
                    {
                      sx: { mb: 2 },
                      children: [
                        _jsxs(Stack, {
                          direction: 'row',
                          spacing: 1,
                          alignItems: 'center',
                          children: [
                            _jsx(Typography, {
                              variant: 'caption',
                              color: 'text.secondary',
                              children: message.role.toUpperCase(),
                            }),
                            message.cached &&
                              _jsx(Chip, { label: 'CACHED', color: 'success', size: 'small' }),
                            message.provider &&
                              _jsx(Chip, { label: message.provider, color: 'info', size: 'small' }),
                            message.isStreaming && _jsx(CircularProgress, { size: 12 }),
                          ],
                        }),
                        _jsx(Box, {
                          sx: {
                            mt: 1,
                            px: 1.25,
                            py: 1,
                            borderRadius: 3,
                            bgcolor: t =>
                              message.role === 'user'
                                ? t.palette.mode === 'dark'
                                  ? 'rgba(26,115,232,0.14)'
                                  : 'rgba(26,115,232,0.08)'
                                : t.palette.background.paper,
                            border: t => `1px solid ${t.palette.divider}`,
                            opacity: 0,
                            animation: 'fadeIn 200ms ease forwards',
                          },
                          children: _jsx(Markdown, {
                            children:
                              message.role === 'assistant' && message.isStreaming
                                ? currentStreamingMessage || message.content
                                : message.content,
                          }),
                        }),
                        message.role === 'assistant' &&
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
                                    onClick: () => copyToClipboard(message.content, i),
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
                                    onClick: () => resendForRegeneration(i),
                                    'aria-label': 'Regenerate response',
                                    disabled: connectionStatus !== 'connected',
                                    children: _jsx(ReplayIcon, { fontSize: 'small' }),
                                  }),
                                }),
                              }),
                            ],
                          }),
                        message.role === 'assistant' &&
                          message.isStreaming &&
                          isStreaming &&
                          _jsx(Box, {
                            sx: { mt: 1 },
                            children: _jsx(Typography, {
                              variant: 'caption',
                              color: 'primary',
                              children: '\u258B ',
                            }),
                          }),
                        message.metadata &&
                          _jsxs(Accordion, {
                            sx: { mt: 1 },
                            children: [
                              _jsx(AccordionSummary, {
                                expandIcon: _jsx(ExpandMoreIcon, {}),
                                children: _jsx(Typography, {
                                  variant: 'caption',
                                  children: 'Show Details',
                                }),
                              }),
                              _jsx(AccordionDetails, {
                                children: _jsx('pre', {
                                  style: {
                                    fontSize: '0.75rem',
                                    maxHeight: '200px',
                                    overflow: 'auto',
                                  },
                                  children: JSON.stringify(message.metadata, null, 2),
                                }),
                              }),
                            ],
                          }),
                      ],
                    },
                    i
                  )
                ),
                _jsx('div', { ref: messagesEndRef }),
              ],
            }),
            _jsxs(Stack, {
              direction: 'row',
              spacing: 1,
              alignItems: 'center',
              children: [
                _jsx(TextField, {
                  fullWidth: true,
                  size: 'small',
                  placeholder: isStreaming ? 'Generating response...' : 'Type a message...',
                  value: input,
                  onChange: e => setInput(e.target.value),
                  disabled: isStreaming,
                  onKeyDown: e => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      sendStreamingMessage();
                    }
                  },
                }),
                _jsx(IconButton, {
                  color: 'primary',
                  onClick: sendStreamingMessage,
                  disabled: isStreaming || !input.trim() || connectionStatus !== 'connected',
                  children: isStreaming ? _jsx(CircularProgress, { size: 24 }) : _jsx(SendIcon, {}),
                }),
              ],
            }),
            _jsxs(Stack, {
              direction: 'row',
              spacing: 2,
              alignItems: 'center',
              children: [
                _jsx(FormControlLabel, {
                  control: _jsx(Switch, {
                    checked: streamingEnabled,
                    onChange: e => setStreamingEnabled(e.target.checked),
                  }),
                  label: 'Enable Streaming',
                }),
                _jsx(Button, {
                  variant: 'outlined',
                  size: 'small',
                  onClick: connectWebSocket,
                  disabled: connectionStatus === 'connected' || connectionStatus === 'connecting',
                  children: 'Reconnect',
                }),
                connectionStatus === 'error' &&
                  _jsx(Alert, {
                    severity: 'warning',
                    sx: { flex: 1 },
                    children: 'Connection lost. Click reconnect to restore streaming.',
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
export default StreamingChatPanel;
//# sourceMappingURL=StreamingChatPanel.js.map
