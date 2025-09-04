import { configureStore, createSlice, PayloadAction } from '@reduxjs/toolkit';

interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
  isStreaming?: boolean;
  cached?: boolean;
  provider?: string;
  metadata?: any;
}

interface AppState {
  chatHistory: ChatMessage[];
  approvals: { id: number; content: string }[];
  stateSummary: any;
  streamingStatus: {
    isStreaming: boolean;
    connectionStatus: string;
    currentProvider: string | null;
  };
}

const initialState: AppState = {
  chatHistory: [],
  approvals: [],
  stateSummary: null,
  streamingStatus: {
    isStreaming: false,
    connectionStatus: 'disconnected',
    currentProvider: null,
  },
};

const appSlice = createSlice({
  name: 'app',
  initialState,
  reducers: {
    addChat(state, action: PayloadAction<ChatMessage>) {
      state.chatHistory.push({
        ...action.payload,
        timestamp: action.payload.timestamp || new Date(),
      });
    },
    updateLastMessage(state, action: PayloadAction<string>) {
      if (state.chatHistory.length > 0) {
        const lastMessage = state.chatHistory[state.chatHistory.length - 1];
        if (lastMessage.role === 'assistant') {
          lastMessage.content = action.payload;
        }
      }
    },
    updateStreamingStatus(
      state,
      action: PayloadAction<Partial<typeof initialState.streamingStatus>>
    ) {
      state.streamingStatus = { ...state.streamingStatus, ...action.payload };
    },
    finalizeStreamingMessage(state, action: PayloadAction<{ content: string; metadata?: any }>) {
      if (state.chatHistory.length > 0) {
        const lastMessage = state.chatHistory[state.chatHistory.length - 1];
        if (lastMessage.role === 'assistant' && lastMessage.isStreaming) {
          lastMessage.content = action.payload.content;
          lastMessage.isStreaming = false;
          lastMessage.metadata = action.payload.metadata;
        }
      }
      state.streamingStatus.isStreaming = false;
    },
    setApprovals(state, action: PayloadAction<{ id: number; content: string }[]>) {
      state.approvals = action.payload;
    },
    setStateSummary(state, action: PayloadAction<any>) {
      state.stateSummary = action.payload;
    },
  },
});

export const {
  addChat,
  updateLastMessage,
  updateStreamingStatus,
  finalizeStreamingMessage,
  setApprovals,
  setStateSummary,
} = appSlice.actions;

export const store = configureStore({ reducer: appSlice.reducer });
export const makeStore = () => configureStore({ reducer: appSlice.reducer });
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
