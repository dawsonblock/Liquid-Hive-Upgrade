import CheckIcon from '@mui/icons-material/Check';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CacheIcon from '@mui/icons-material/Memory';
import StreamIcon from '@mui/icons-material/PlayArrow';
import RefreshIcon from '@mui/icons-material/Refresh';
import ReplayIcon from '@mui/icons-material/Replay';
import SendIcon from '@mui/icons-material/Send';
import StopIcon from '@mui/icons-material/Stop';
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
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';

import { useProviders } from '../contexts/ProvidersContext';
import { getBackendHttpBase, getBackendWsBase } from '../services/env';
import type { RootState } from '../store';
import { addChat, updateLastMessage, finalizeStreamingMessage } from '../store';

import ContextSidebar from './ContextSidebar';
import Markdown from './Markdown';

interface StreamingMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  isStreaming?: boolean;
  cached?: boolean;
  provider?: string;
  metadata?: any;
}

type StreamingChatPanelProps = Record<string, never>;

const StreamingChatPanel: React.FC<StreamingChatPanelProps> = () => {
  // State management
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingEnabled, setStreamingEnabled] = useState(true);
  const [connectionStatus, setConnectionStatus] = useState<
    'disconnected' | 'connecting' | 'connected' | 'error'
  >('disconnected');
  const [currentStreamingMessage, setCurrentStreamingMessage] = useState('');
  const [streamMetadata, setStreamMetadata] = useState<any>(null);
  const [cacheAnalytics, setCacheAnalytics] = useState<any>(null);
  const [cacheLoading, setCacheLoading] = useState<boolean>(false);
  const { providers, loading: providersLoading, refresh: refreshProviders } = useProviders();

  // Context and metadata state
  const [lastContext, setLastContext] = useState<string | undefined>();
  const [lastReasoning, setLastReasoning] = useState<string | undefined>();
  const [lastIntent, setLastIntent] = useState<string | undefined>();
  const [lastRationale, setLastRationale] = useState<string | undefined>();

  // Redux
  const dispatch = useDispatch();
  const history = useSelector((s: RootState) => s.chatHistory);

  // WebSocket reference
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);

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
      // TODO: Replace with proper logging
        console.log('🔗 Connected to streaming chat WebSocket');
    };

    ws.onmessage = event => {
      try {
        const data = JSON.parse(event.data);
        handleWebSocketMessage(data);
      } catch (error) {
        // TODO: Replace with proper error handling
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      setConnectionStatus('disconnected');
      setIsStreaming(false);
      // TODO: Replace with proper logging
        console.log('🔌 WebSocket connection closed');
    };

    ws.onerror = error => {
      setConnectionStatus('error');
      setIsStreaming(false);
      // TODO: Replace with proper error handling
        console.error('WebSocket error:', error);
    };

    wsRef.current = ws;
  }, []);

  // Handle WebSocket messages
  const handleWebSocketMessage = (data: any) => {
    switch (data.type) {
      case 'stream_start':
        setIsStreaming(true);
        setCurrentStreamingMessage('');
        setStreamMetadata(data.metadata);
        // TODO: Replace with proper logging
        console.log('🚀 Stream started:', data.metadata);
        break;

      case 'chunk':
        setCurrentStreamingMessage(prev => prev + data.content);

        // Update the last assistant message in real-time
        if (history.length > 0 && history[history.length - 1]?.role === 'assistant') {
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
        // TODO: Replace with proper logging
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
        // TODO: Replace with proper error handling
        console.error('❌ Streaming error:', data.error);
        break;

      default:
        // TODO: Replace with proper logging
        console.log('📨 Unknown message type:', data.type);
    }
  };

  const resendForRegeneration = useCallback(
    (idx: number) => {
      // Find the nearest previous user prompt and resend it
      for (let j = idx - 1; j >= 0; j--) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const msg: any = (history as any)[j];
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

  const copyToClipboard = async (text: string, idx: number) => {
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
      // TODO: Replace with proper error handling
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
    const el = messagesEndRef.current as any;
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

  return (
    <Grid container spacing={3}>
      <Grid item xs={12} md={8}>
        <Stack spacing={2}>
          {/* Status Bar */}
          <Paper variant='outlined' sx={{ p: 1.5, bgcolor: 'background.paper', borderRadius: 4 }}>
            <Stack direction='row' spacing={2} alignItems='center'>
              <Chip
                icon={
                  connectionStatus === 'connecting' ? (
                    <CircularProgress size={16} />
                  ) : (
                    <StreamIcon />
                  )
                }
                label={`Streaming: ${connectionStatus}`}
                color={getConnectionStatusColor()}
                variant='outlined'
                size='small'
              />

              {streamMetadata && (
                <Chip
                  icon={<CacheIcon />}
                  label={
                    streamMetadata.cached
                      ? `Cache Hit${typeof streamMetadata.cache_similarity === 'number' ? ` (${(streamMetadata.cache_similarity * 100).toFixed(0)}%)` : ''}`
                      : 'Live Generation'
                  }
                  color={streamMetadata.cached ? 'success' : 'primary'}
                  variant='outlined'
                  size='small'
                />
              )}

              {cacheAnalytics && (
                <Chip
                  icon={<CacheIcon />}
                  label={`Cache: ${Math.round((cacheAnalytics.hit_rate || 0) * 100)}%`}
                  color={(cacheAnalytics.hit_rate || 0) > 0.5 ? 'success' : 'default'}
                  variant='outlined'
                  size='small'
                />
              )}

              {isStreaming && (
                <Typography variant='caption' color='primary'>
                  Generating response...
                </Typography>
              )}

              <Box sx={{ flex: 1 }} />
              {isStreaming && (
                <Button
                  size='small'
                  color='error'
                  variant='outlined'
                  onClick={stopGeneration}
                  startIcon={<StopIcon />}
                >
                  Stop
                </Button>
              )}
              <Button
                size='small'
                variant='outlined'
                onClick={refreshProviders}
                startIcon={providersLoading ? <CircularProgress size={14} /> : <RefreshIcon />}
              >
                Refresh Providers
              </Button>
              <Button
                size='small'
                variant='outlined'
                onClick={refreshCacheAnalytics}
                startIcon={cacheLoading ? <CircularProgress size={14} /> : <CacheIcon />}
              >
                Cache Analytics
              </Button>
            </Stack>
          </Paper>

          {/* Provider chips */}
          {providers && Object.keys(providers).length > 0 && (
            <Paper variant='outlined' sx={{ p: 1 }}>
              <Stack direction='row' spacing={1} alignItems='center' flexWrap='wrap'>
                {Object.entries(providers).map(([name, info]) => (
                  <Chip
                    key={name}
                    size='small'
                    label={`${name}: ${info?.status || 'unknown'}`}
                    color={
                      (info?.status === 'healthy'
                        ? 'success'
                        : info?.status
                          ? 'warning'
                          : 'default') as any
                    }
                  />
                ))}
              </Stack>
            </Paper>
          )}

          {/* Chat History */}
          <Paper
            variant='outlined'
            sx={{
              p: 2.5,
              height: 520,
              overflowY: 'auto',
              bgcolor: t =>
                t.palette.mode === 'dark' ? 'rgba(2,6,23,0.6)' : 'rgba(255,255,255,0.9)',
              borderRadius: 4,
            }}
          >
            {history.length === 0 && (
              <Typography variant='body2' color='text.secondary'>
                Start the conversation with the Enhanced Cognitive Core. Streaming is enabled for
                real-time responses.
              </Typography>
            )}

            {history.map((message, i) => (
              <Box key={i} sx={{ mb: 2 }}>
                <Stack direction='row' spacing={1} alignItems='center'>
                  <Typography variant='caption' color='text.secondary'>
                    {message.role.toUpperCase()}
                  </Typography>

                  {message.cached && <Chip label='CACHED' color='success' size='small' />}

                  {message.provider && <Chip label={message.provider} color='info' size='small' />}

                  {message.isStreaming && <CircularProgress size={12} />}
                </Stack>

                <Box
                  sx={{
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
                  }}
                >
                  <Markdown>
                    {message.role === 'assistant' && message.isStreaming
                      ? currentStreamingMessage || message.content
                      : message.content}
                  </Markdown>
                </Box>

                {message.role === 'assistant' && (
                  <Stack direction='row' spacing={1} sx={{ mt: 0.5 }}>
                    <Tooltip title={copiedIdx === i ? 'Copied' : 'Copy message'}>
                      <span>
                        <IconButton
                          size='small'
                          onClick={() => copyToClipboard(message.content, i)}
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
                          onClick={() => resendForRegeneration(i)}
                          aria-label='Regenerate response'
                          disabled={connectionStatus !== 'connected'}
                        >
                          <ReplayIcon fontSize='small' />
                        </IconButton>
                      </span>
                    </Tooltip>
                  </Stack>
                )}

                {/* Show streaming indicator for active streaming message */}
                {message.role === 'assistant' && message.isStreaming && isStreaming && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant='caption' color='primary'>
                      ▋ {/* Cursor indicator */}
                    </Typography>
                  </Box>
                )}

                {/* Metadata accordion for detailed info */}
                {message.metadata && (
                  <Accordion sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant='caption'>Show Details</Typography>
                    </AccordionSummary>
                    <AccordionDetails>
                      <pre style={{ fontSize: '0.75rem', maxHeight: '200px', overflow: 'auto' }}>
                        {JSON.stringify(message.metadata, null, 2)}
                      </pre>
                    </AccordionDetails>
                  </Accordion>
                )}
              </Box>
            ))}

            <div ref={messagesEndRef} />
          </Paper>

          {/* Input Area */}
          <Stack direction='row' spacing={1} alignItems='center'>
            <TextField
              fullWidth
              size='small'
              placeholder={isStreaming ? 'Generating response...' : 'Type a message...'}
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={isStreaming}
              onKeyDown={e => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendStreamingMessage();
                }
              }}
            />

            <IconButton
              color='primary'
              onClick={sendStreamingMessage}
              disabled={isStreaming || !input.trim() || connectionStatus !== 'connected'}
            >
              {isStreaming ? <CircularProgress size={24} /> : <SendIcon />}
            </IconButton>
          </Stack>

          {/* Streaming Controls */}
          <Stack direction='row' spacing={2} alignItems='center'>
            <FormControlLabel
              control={
                <Switch
                  checked={streamingEnabled}
                  onChange={e => setStreamingEnabled(e.target.checked)}
                />
              }
              label='Enable Streaming'
            />

            <Button
              variant='outlined'
              size='small'
              onClick={connectWebSocket}
              disabled={connectionStatus === 'connected' || connectionStatus === 'connecting'}
            >
              Reconnect
            </Button>

            {connectionStatus === 'error' && (
              <Alert severity='warning' sx={{ flex: 1 }}>
                Connection lost. Click reconnect to restore streaming.
              </Alert>
            )}
          </Stack>
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

export default StreamingChatPanel;
