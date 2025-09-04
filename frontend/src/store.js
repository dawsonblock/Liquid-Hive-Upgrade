import { configureStore, createSlice } from '@reduxjs/toolkit';
const initialState = {
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
    addChat(state, action) {
      state.chatHistory.push({
        ...action.payload,
        timestamp: action.payload.timestamp || new Date(),
      });
    },
    updateLastMessage(state, action) {
      if (state.chatHistory.length > 0) {
        const lastMessage = state.chatHistory[state.chatHistory.length - 1];
        if (lastMessage.role === 'assistant') {
          lastMessage.content = action.payload;
        }
      }
    },
    updateStreamingStatus(state, action) {
      state.streamingStatus = { ...state.streamingStatus, ...action.payload };
    },
    finalizeStreamingMessage(state, action) {
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
    setApprovals(state, action) {
      state.approvals = action.payload;
    },
    setStateSummary(state, action) {
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
//# sourceMappingURL=store.js.map
