import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getProvidersStatus } from '../services/api';

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

const ProvidersContext = createContext<ProvidersContextValue | undefined>(undefined);

export const ProvidersProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [providers, setProviders] = useState<ProvidersMap>({});
  const [loading, setLoading] = useState<boolean>(false);
  const [lastUpdated, setLastUpdated] = useState<number | undefined>(undefined);
  const [autoRefresh, setAutoRefresh] = useState<boolean>(true);
  const [intervalMs, setIntervalMs] = useState<number>(15000);

  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const ps = await getProvidersStatus();
      if (ps?.providers) setProviders(ps.providers);
      setLastUpdated(Date.now());
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // Initial fetch
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (!autoRefresh) return;
    const id = window.setInterval(() => {
      refresh();
    }, Math.max(5000, intervalMs));
    return () => window.clearInterval(id);
  }, [autoRefresh, intervalMs, refresh]);

  const value = useMemo<ProvidersContextValue>(() => ({
    providers,
    loading,
    lastUpdated,
    refresh,
    autoRefresh,
    setAutoRefresh,
    intervalMs,
    setIntervalMs,
  }), [providers, loading, lastUpdated, refresh, autoRefresh, intervalMs]);

  return (
    <ProvidersContext.Provider value={value}>
      {children}
    </ProvidersContext.Provider>
  );
};

export function useProviders() {
  const ctx = useContext(ProvidersContext);
  if (!ctx) throw new Error('useProviders must be used within ProvidersProvider');
  return ctx;
}
