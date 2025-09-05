import React from 'react';
type ProvidersMap = Record<string, any>;
type ProvidersContextValue = {
    providers: ProvidersMap;
    loading: boolean;
    lastUpdated?: number;
    refresh: () => Promise<void>;
    autoRefresh: boolean;
    setAutoRefresh: (v: boolean) => void;
    intervalMs: number;
    setIntervalMs: (ms: number) => void;
};
export declare const ProvidersProvider: React.FC<{
    children: React.ReactNode;
}>;
export declare function useProviders(): ProvidersContextValue;
export {};
//# sourceMappingURL=ProvidersContext.d.ts.map