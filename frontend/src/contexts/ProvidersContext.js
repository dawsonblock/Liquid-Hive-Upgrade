import { jsx as _jsx } from 'react/jsx-runtime';
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import { getProvidersStatus } from '../services/api';
const ProvidersContext = createContext(undefined);
export const ProvidersProvider = ({ children }) => {
  const [providers, setProviders] = useState({});
  const [loading, setLoading] = useState(false);
  const [lastUpdated, setLastUpdated] = useState(undefined);
  const [autoRefresh, setAutoRefresh] = useState(() => {
    const saved = localStorage.getItem('LH_PROVIDERS_AUTO_REFRESH');
    return saved !== null ? saved === '1' : true;
  });
  const [intervalMs, setIntervalMs] = useState(() => {
    const saved = localStorage.getItem('LH_PROVIDERS_INTERVAL_MS');
    const n = saved ? parseInt(saved, 10) : 15000;
    return Number.isFinite(n) && n >= 1000 ? n : 15000;
  });
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
    const id = window.setInterval(
      () => {
        refresh();
      },
      Math.max(5000, intervalMs)
    );
    return () => window.clearInterval(id);
  }, [autoRefresh, intervalMs, refresh]);
  // Persist preferences
  useEffect(() => {
    try {
      localStorage.setItem('LH_PROVIDERS_AUTO_REFRESH', autoRefresh ? '1' : '0');
    } catch {}
  }, [autoRefresh]);
  useEffect(() => {
    try {
      localStorage.setItem('LH_PROVIDERS_INTERVAL_MS', String(intervalMs));
    } catch {}
  }, [intervalMs]);
  const value = useMemo(
    () => ({
      providers,
      loading,
      lastUpdated,
      refresh,
      autoRefresh,
      setAutoRefresh,
      intervalMs,
      setIntervalMs,
    }),
    [providers, loading, lastUpdated, refresh, autoRefresh, intervalMs]
  );
  return _jsx(ProvidersContext.Provider, { value: value, children: children });
};
export function useProviders() {
  const ctx = useContext(ProvidersContext);
  if (!ctx) throw new Error('useProviders must be used within ProvidersProvider');
  return ctx;
}
//# sourceMappingURL=ProvidersContext.js.map
