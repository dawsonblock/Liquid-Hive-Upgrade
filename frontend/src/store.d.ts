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
  approvals: {
    id: number;
    content: string;
  }[];
  stateSummary: any;
  streamingStatus: {
    isStreaming: boolean;
    connectionStatus: string;
    currentProvider: string | null;
  };
}
export declare const addChat: import('@reduxjs/toolkit').ActionCreatorWithPayload<
    ChatMessage,
    'app/addChat'
  >,
  updateLastMessage: import('@reduxjs/toolkit').ActionCreatorWithPayload<
    string,
    'app/updateLastMessage'
  >,
  updateStreamingStatus: import('@reduxjs/toolkit').ActionCreatorWithPayload<
    Partial<{
      isStreaming: boolean;
      connectionStatus: string;
      currentProvider: string | null;
    }>,
    'app/updateStreamingStatus'
  >,
  finalizeStreamingMessage: import('@reduxjs/toolkit').ActionCreatorWithPayload<
    {
      content: string;
      metadata?: any;
    },
    'app/finalizeStreamingMessage'
  >,
  setApprovals: import('@reduxjs/toolkit').ActionCreatorWithPayload<
    {
      id: number;
      content: string;
    }[],
    'app/setApprovals'
  >,
  setStateSummary: import('@reduxjs/toolkit').ActionCreatorWithPayload<any, 'app/setStateSummary'>;
export declare const store: import('@reduxjs/toolkit').EnhancedStore<
  AppState,
  import('redux').UnknownAction,
  import('@reduxjs/toolkit').Tuple<
    [
      import('redux').StoreEnhancer<{
        dispatch: import('redux-thunk').ThunkDispatch<
          AppState,
          undefined,
          import('redux').UnknownAction
        >;
      }>,
      import('redux').StoreEnhancer,
    ]
  >
>;
export declare const makeStore: () => import('@reduxjs/toolkit').EnhancedStore<
  AppState,
  import('redux').UnknownAction,
  import('@reduxjs/toolkit').Tuple<
    [
      import('redux').StoreEnhancer<{
        dispatch: import('redux-thunk').ThunkDispatch<
          AppState,
          undefined,
          import('redux').UnknownAction
        >;
      }>,
      import('redux').StoreEnhancer,
    ]
  >
>;
export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
export {};
//# sourceMappingURL=store.d.ts.map
