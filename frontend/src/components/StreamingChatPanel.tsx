import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import CacheIcon from '@mui/icons-material/Memory';
import StreamIcon from '@mui/icons-material/PlayArrow';
import RefreshIcon from '@mui/icons-material/Refresh';
import SendIcon from '@mui/icons-material/Send';
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
  Typography
} from '@mui/material';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import { useDispatch, useSelector } from 'react-redux';
import { useProviders } from '../contexts/ProvidersContext';
import { getBackendHttpBase, getBackendWsBase } from '../services/env';
import type { RootState } from '../store';
import { addChat, updateLastMessage } from '../store';
import ContextSidebar from './ContextSidebar';

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
  const [connectionStatus, setConnectionStatus] = useState<'disconnected' | 'connecting' | 'connected' | 'error'>('disconnected');
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

    ws.onmessage = (event) => {
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

    ws.onerror = (error) => {
      setConnectionStatus('error');
      setIsStreaming(false);
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
        dispatch(addChat({
          role: 'assistant',
          content: data.content,
          timestamp: new Date(),
          cached: true,
          metadata: data.metadata
        }));
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
        dispatch(addChat({
          role: 'assistant',
          content: `Error: ${data.error}`,
          timestamp: new Date(),
          metadata: { error: true }
        }));
        console.error('❌ Streaming error:', data.error);
        break;

      default:
        console.log('📨 Unknown message type:', data.type);
    }
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
    dispatch(addChat({
      role: 'user',
      content: input,
      timestamp: new Date()
    }));

    // Add placeholder for assistant response
    dispatch(addChat({
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      isStreaming: true
    }));

    // Send query via WebSocket
    const message = {
      q: input,
      stream: streamingEnabled
    };

    wsRef.current.send(JSON.stringify(message));
    setInput('');
  };

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
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
      case 'connected': return 'success';
      case 'connecting': return 'warning';
      case 'error': return 'error';
      default: return 'default';
    }
  };

  return (
    <Grid container spacing={2}>
      <Grid item xs={12} md={8}>
        <Stack spacing={2}>
          {/* Status Bar */}
          <Paper variant="outlined" sx={{ p: 1, bgcolor: 'background.paper' }}>
            <Stack direction="row" spacing={2} alignItems="center">
              <Chip
                icon={connectionStatus === 'connecting' ? <CircularProgress size={16} /> : <StreamIcon />}
                label={`Streaming: ${connectionStatus}`}
                color={getConnectionStatusColor()}
                variant="outlined"
                size="small"
              />

              {streamMetadata && (
                <Chip
                  icon={<CacheIcon />}
                  label={streamMetadata.cached ? (`Cache Hit${typeof streamMetadata.cache_similarity === 'number' ? ` (${(streamMetadata.cache_similarity * 100).toFixed(0)}%)` : ''}`) : 'Live Generation'}
                  color={streamMetadata.cached ? 'success' : 'primary'}
                  variant="outlined"
                  size="small"
                />
              )}

              {cacheAnalytics && (
                <Chip
                  icon={<CacheIcon />}
                  label={`Cache: ${Math.round((cacheAnalytics.hit_rate || 0) * 100)}%`}
                  color={(cacheAnalytics.hit_rate || 0) > 0.5 ? 'success' : 'default'}
                  variant="outlined"
                  size="small"
                />
              )}

              {isStreaming && (
                <Typography variant="caption" color="primary">
                  Generating response...
                </Typography>
              )}

              <Box sx={{ flex: 1 }} />
              <Button
                size="small"
                variant="outlined"
                onClick={refreshProviders}
                startIcon={providersLoading ? <CircularProgress size={14} /> : <RefreshIcon />}
              >
                Refresh Providers
              </Button>
              <Button
                size="small"
                variant="outlined"
                onClick={refreshCacheAnalytics}
                startIcon={cacheLoading ? <CircularProgress size={14} /> : <CacheIcon />}
              >
                Cache Analytics
              </Button>
            </Stack>
          </Paper>

          {/* Provider chips */}
          {providers && Object.keys(providers).length > 0 && (
            <Paper variant="outlined" sx={{ p: 1 }}>
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                {Object.entries(providers).map(([name, info]) => (
                  <Chip key={name} size="small" label={`${name}: ${info?.status || 'unknown'}`}
                    color={(info?.status === 'healthy' ? 'success' : (info?.status ? 'warning' : 'default')) as any}
                  />
                ))}
              </Stack>
            </Paper>
          )}

          {/* Chat History */}
          <Paper variant="outlined" sx={{ p: 2, height: 500, overflowY: 'auto', bgcolor: 'background.default' }}>
            {history.length === 0 && (
              <Typography variant="body2" color="text.secondary">
                Start the conversation with the Enhanced Cognitive Core.
                Streaming is enabled for real-time responses.
              </Typography>
            )}

            {history.map((message, i) => (
              <Box key={i} sx={{ mb: 2 }}>
                <Stack direction="row" spacing={1} alignItems="center">
                  <Typography variant="caption" color="text.secondary">
                    {message.role.toUpperCase()}
                  </Typography>

                  {message.cached && (
                    <Chip label="CACHED" color="success" size="small" />
                  )}

                  {message.provider && (
                    <Chip label={message.provider} color="info" size="small" />
                  )}

                  {message.isStreaming && (
                    <CircularProgress size={12} />
                  )}
                </Stack>

                <Box sx={{ mt: 1 }}>
                  <ReactMarkdown>
                    {message.role === 'assistant' && message.isStreaming
                      ? currentStreamingMessage || message.content
                      : message.content
                    }
                  </ReactMarkdown>
                </Box>

                {/* Show streaming indicator for active streaming message */}
                {message.role === 'assistant' && message.isStreaming && isStreaming && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="primary">
                      ▋ {/* Cursor indicator */}
                    </Typography>
                  </Box>
                )}

                {/* Metadata accordion for detailed info */}
                {message.metadata && (
                  <Accordion sx={{ mt: 1 }}>
                    <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                      <Typography variant="caption">Show Details</Typography>
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
          <Stack direction="row" spacing={1} alignItems="center">
            <TextField
              fullWidth
              size="small"
              placeholder={isStreaming ? "Generating response..." : "Type a message..."}
              value={input}
              onChange={e => setInput(e.target.value)}
              disabled={isStreaming}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  sendStreamingMessage();
                }
              }}
            />

            <IconButton
              color="primary"
              onClick={sendStreamingMessage}
              disabled={isStreaming || !input.trim() || connectionStatus !== 'connected'}
            >
              {isStreaming ? <CircularProgress size={24} /> : <SendIcon />}
            </IconButton>
          </Stack>

          {/* Streaming Controls */}
          <Stack direction="row" spacing={2} alignItems="center">
            <FormControlLabel
              control={
                <Switch
                  checked={streamingEnabled}
                  onChange={e => setStreamingEnabled(e.target.checked)}
                />
              }
              label="Enable Streaming"
            />

            <Button
              variant="outlined"
              size="small"
              onClick={connectWebSocket}
              disabled={connectionStatus === 'connected' || connectionStatus === 'connecting'}
            >
              Reconnect
            </Button>

            {connectionStatus === 'error' && (
              <Alert severity="warning" sx={{ flex: 1 }}>
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