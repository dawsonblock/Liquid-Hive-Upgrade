import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  TextField,
  IconButton,
  Stack,
  Typography,
  Button,
  Avatar,
  Chip,
  Tooltip,
  Fade,
  Zoom,
  Slide,
  Divider,
  Badge,
  Menu,
  MenuItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachFileIcon,
  Mic as MicIcon,
  MicOff as MicOffIcon,
  Clear as ClearIcon,
  MoreVert as MoreVertIcon,
  ContentCopy as CopyIcon,
  ThumbUp as ThumbUpIcon,
  ThumbDown as ThumbDownIcon,
  Refresh as RefreshIcon,
  Settings as SettingsIcon,
  Fullscreen as FullscreenIcon,
  FullscreenExit as FullscreenExitIcon,
} from '@mui/icons-material';
import { useTheme } from '@mui/material/styles';
import { useDispatch, useSelector } from 'react-redux';
import { RootState } from '../store';

interface Message {
  id: string;
  content: string;
  sender: 'user' | 'assistant' | 'system';
  timestamp: Date;
  isTyping?: boolean;
  attachments?: File[];
  metadata?: {
    tokens?: number;
    model?: string;
    confidence?: number;
  };
}

const EnhancedChatPanel: React.FC = () => {
  const theme = useTheme();
  const dispatch = useDispatch();
  const chatHistory = useSelector((state: RootState) => state.chatHistory);

  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Voice recognition setup
  useEffect(() => {
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = false;
      recognitionRef.current.interimResults = false;
      recognitionRef.current.lang = 'en-US';

      recognitionRef.current.onresult = (event: SpeechRecognitionEvent) => {
        const transcript = event.results[0][0].transcript;
        setInput(transcript);
        setIsRecording(false);
      };

      recognitionRef.current.onerror = (event: SpeechRecognitionErrorEvent) => {
        // TODO: Replace with proper error handling
        console.error('Speech recognition error:', event.error);
        setIsRecording(false);
      };

      recognitionRef.current.onend = () => {
        setIsRecording(false);
      };
    }
  }, []);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      sender: 'user',
      timestamp: new Date(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    // Simulate AI response
    setTimeout(() => {
      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        content: `I understand you said: "${userMessage.content}". This is a simulated response from the Capsule Brain AGI system.`,
        sender: 'assistant',
        timestamp: new Date(),
        metadata: {
          tokens: 150,
          model: 'gpt-4',
          confidence: 0.95,
        },
      };

      setMessages(prev => [...prev, aiMessage]);
      setIsTyping(false);
    }, 2000);
  };

  const handleVoiceToggle = () => {
    if (!recognitionRef.current) return;

    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };

  const handleClear = () => {
    if (window.confirm('Are you sure you want to clear the chat?')) {
      setMessages([]);
    }
  };

  const handleCopy = (content: string) => {
    navigator.clipboard.writeText(content);
  };

  const handleLike = (messageId: string) => {
    // Implement like functionality
    // TODO: Replace with proper logging
        // Message liked: messageId
  };

  const handleDislike = (messageId: string) => {
    // Implement dislike functionality
    // TODO: Replace with proper logging
        // Message disliked: messageId
  };

  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen();
      setIsFullscreen(false);
    }
  };

  const MessageBubble: React.FC<{ message: Message }> = ({ message }) => {
    const isUser = message.sender === 'user';
    const isSystem = message.sender === 'system';

    return (
      <Fade in timeout={300}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: isUser ? 'flex-end' : 'flex-start',
            mb: 2,
            px: 2,
          }}
        >
          <Paper
            elevation={3}
            sx={{
              p: 2,
              maxWidth: '70%',
              backgroundColor: isUser
                ? theme.palette.primary.main
                : isSystem
                ? theme.palette.grey[100]
                : theme.palette.background.paper,
              color: isUser ? theme.palette.primary.contrastText : theme.palette.text.primary,
              borderRadius: isUser ? '20px 20px 5px 20px' : '20px 20px 20px 5px',
              position: 'relative',
            }}
          >
            {!isUser && (
              <Avatar
                sx={{
                  position: 'absolute',
                  left: -20,
                  top: 0,
                  width: 32,
                  height: 32,
                  bgcolor: theme.palette.secondary.main,
                }}
              >
                🧠
              </Avatar>
            )}

            <Typography variant="body1" sx={{ mb: 1 }}>
              {message.content}
            </Typography>

            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                mt: 1,
                opacity: 0.7,
              }}
            >
              <Typography variant="caption">
                {message.timestamp.toLocaleTimeString()}
              </Typography>

              {message.metadata && (
                <Chip
                  size="small"
                  label={`${message.metadata.tokens} tokens`}
                  variant="outlined"
                />
              )}
            </Box>

            {!isUser && (
              <Box sx={{ mt: 1, display: 'flex', gap: 0.5 }}>
                <Tooltip title="Copy">
                  <IconButton size="small" onClick={() => handleCopy(message.content)}>
                    <CopyIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Like">
                  <IconButton size="small" onClick={() => handleLike(message.id)}>
                    <ThumbUpIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
                <Tooltip title="Dislike">
                  <IconButton size="small" onClick={() => handleDislike(message.id)}>
                    <ThumbDownIcon fontSize="small" />
                  </IconButton>
                </Tooltip>
              </Box>
            )}
          </Paper>
        </Box>
      </Fade>
    );
  };

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        position: 'relative',
      }}
    >
      {/* Header */}
      <Paper
        elevation={2}
        sx={{
          p: 2,
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderRadius: 0,
        }}
      >
        <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Avatar sx={{ bgcolor: theme.palette.primary.main }}>🧠</Avatar>
          Capsule Brain AGI
        </Typography>

        <Stack direction="row" spacing={1}>
          <Tooltip title="Settings">
            <IconButton onClick={() => setShowSettings(!showSettings)}>
              <SettingsIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title="Clear Chat">
            <IconButton onClick={handleClear}>
              <ClearIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}>
            <IconButton onClick={toggleFullscreen}>
              {isFullscreen ? <FullscreenExitIcon /> : <FullscreenIcon />}
            </IconButton>
          </Tooltip>

          <IconButton onClick={handleMenuOpen}>
            <MoreVertIcon />
          </IconButton>
        </Stack>
      </Paper>

      {/* Messages */}
      <Box
        sx={{
          flex: 1,
          overflow: 'auto',
          p: 1,
          background: `linear-gradient(135deg, ${theme.palette.background.default} 0%, ${theme.palette.grey[50]} 100%)`,
        }}
      >
        {messages.length === 0 && (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              textAlign: 'center',
              opacity: 0.6,
            }}
          >
            <Typography variant="h4" sx={{ mb: 2 }}>
              🧠
            </Typography>
            <Typography variant="h6" color="textSecondary">
              Welcome to Capsule Brain AGI
            </Typography>
            <Typography variant="body2" color="textSecondary">
              Start a conversation with the AI
            </Typography>
          </Box>
        )}

        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}

        {isTyping && (
          <Fade in>
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'flex-start',
                mb: 2,
                px: 2,
              }}
            >
              <Paper
                elevation={2}
                sx={{
                  p: 2,
                  backgroundColor: theme.palette.background.paper,
                  borderRadius: '20px 20px 20px 5px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 1,
                }}
              >
                <Avatar sx={{ width: 32, height: 32, bgcolor: theme.palette.secondary.main }}>
                  🧠
                </Avatar>
                <Typography variant="body2" color="textSecondary">
                  AGI is thinking...
                </Typography>
                <Box
                  sx={{
                    display: 'flex',
                    gap: 0.5,
                    '& > div': {
                      width: 6,
                      height: 6,
                      borderRadius: '50%',
                      backgroundColor: theme.palette.primary.main,
                      animation: 'pulse 1.4s ease-in-out infinite both',
                      '&:nth-of-type(1)': { animationDelay: '-0.32s' },
                      '&:nth-of-type(2)': { animationDelay: '-0.16s' },
                    },
                  }}
                >
                  <div />
                  <div />
                  <div />
                </Box>
              </Paper>
            </Box>
          </Fade>
        )}

        <div ref={messagesEndRef} />
      </Box>

      {/* Input Area */}
      <Paper
        elevation={3}
        sx={{
          p: 2,
          borderRadius: 0,
          borderTop: `1px solid ${theme.palette.divider}`,
        }}
      >
        <Stack direction="row" spacing={1} alignItems="flex-end">
          <Tooltip title="Attach File">
            <IconButton>
              <AttachFileIcon />
            </IconButton>
          </Tooltip>

          <Tooltip title={isRecording ? "Stop Recording" : "Voice Input"}>
            <IconButton
              onClick={handleVoiceToggle}
              color={isRecording ? 'error' : 'default'}
            >
              {isRecording ? <MicOffIcon /> : <MicIcon />}
            </IconButton>
          </Tooltip>

          <TextField
            ref={inputRef}
            fullWidth
            multiline
            maxRows={4}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your message..."
            variant="outlined"
            size="small"
            onKeyPress={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                borderRadius: 3,
              },
            }}
          />

          <Tooltip title="Send">
            <IconButton
              onClick={handleSend}
              disabled={!input.trim()}
              color="primary"
              sx={{
                bgcolor: theme.palette.primary.main,
                color: theme.palette.primary.contrastText,
                '&:hover': {
                  bgcolor: theme.palette.primary.dark,
                },
                '&:disabled': {
                  bgcolor: theme.palette.action.disabled,
                },
              }}
            >
              <SendIcon />
            </IconButton>
          </Tooltip>
        </Stack>
      </Paper>

      {/* Context Menu */}
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={handleMenuClose}
      >
        <MenuItem onClick={handleMenuClose}>
          <ListItemIcon>
            <RefreshIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Refresh</ListItemText>
        </MenuItem>
        <MenuItem onClick={handleMenuClose}>
          <ListItemIcon>
            <SettingsIcon fontSize="small" />
          </ListItemIcon>
          <ListItemText>Settings</ListItemText>
        </MenuItem>
      </Menu>

      <style>{`
        @keyframes pulse {
          0%, 80%, 100% {
            transform: scale(0);
            opacity: 0.5;
          }
          40% {
            transform: scale(1);
            opacity: 1;
          }
        }
        .pulse {
          animation: pulse 1.4s infinite ease-in-out;
        }
        .pulse:nth-child(1) { animation-delay: -0.32s; }
        .pulse:nth-child(2) { animation-delay: -0.16s; }
      `}</style>
    </Box>
  );
};

export default EnhancedChatPanel;
