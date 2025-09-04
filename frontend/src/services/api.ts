import axios from 'axios';
import { getBackendHttpBase } from './env';

// If an explicit backend base exists, point axios to it. Otherwise, rely on Vite dev proxy via '/api'.
const httpBase = getBackendHttpBase();
const baseURL = httpBase ? `${httpBase}/api` : '/api';

export const api = axios.create({
  baseURL,
  headers: { 'Content-Type': 'application/json' },
});

export const fetchState = () => api.get('/state').then(r => r.data);
export const postChat = (q: string) =>
  api.post('/chat?q=' + encodeURIComponent(q)).then(r => r.data);

export const postVision = (form: FormData, groundingRequired: boolean) =>
  api
    .post('/vision?grounding_required=' + String(groundingRequired), form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    .then(r => r.data);

export const getApprovals = () => api.get('/approvals').then(r => r.data);
export const approveProposal = (id: number) =>
  api.post(`/approvals/${id}/approve`).then(r => r.data);
export const denyProposal = (id: number) => api.post(`/approvals/${id}/deny`).then(r => r.data);

export const getAdaptersState = () => api.get('/adapters/state').then(r => r.data);
export const promoteAdapter = (role: string) =>
  api.post(`/adapters/promote/${encodeURIComponent(role)}`).then(r => r.data);

export const getGovernor = () => api.get('/config/governor').then(r => r.data);
export const setGovernor = (enabled: boolean, force_deepseek_r1: boolean) =>
  api.post('/config/governor', { enabled, force_deepseek_r1 }).then(r => r.data);

// Health endpoint to check backend connectivity
export const health = async () => {
  try {
    const res = await api.get('/healthz');
    return { ok: res.status === 200, data: res.data };
  } catch (_e) {
    return { ok: false, data: null };
  }
};

export const startTraining = () => api.post('/train').then(r => r.data);

export const previewAutopromote = () => api.get('/autonomy/autopromote/preview').then(r => r.data);

// New secrets health endpoint
export const getSecretsHealth = () => api.get('/secrets/health').then(r => r.data);

// Secrets management helpers
export const secretExists = (name: string) =>
  api
    .get(`/secrets/exists`, { params: { name } })
    .then(r => r.data as { name: string; exists: boolean });

export const setSecret = (name: string, value: any, adminToken?: string) =>
  api
    .post(
      '/secrets/set',
      { name, value },
      {
        headers: adminToken ? { 'x-admin-token': adminToken } : undefined,
      }
    )
    .then(r => r.data as { status?: string; error?: string; provider?: string });

export const reloadRouterSecrets = (adminToken?: string) =>
  api
    .post(
      '/admin/router/reload-secrets',
      {},
      {
        headers: adminToken ? { 'x-admin-token': adminToken } : undefined,
      }
    )
    .then(r => r.data as { status?: string; error?: string });

// Warm Qwen CPU provider (loads local model)
export const warmQwenProvider = (adminToken?: string) =>
  api
    .post(
      '/admin/providers/qwen/warm',
      {},
      {
        headers: adminToken ? { 'x-admin-token': adminToken } : undefined,
      }
    )
    .then(r => r.data as { status?: string; error?: string; provider?: string; model?: string });

// Providers status
export const getProvidersStatus = () =>
  api.get('/providers').then(
    r =>
      r.data as {
        providers?: Record<string, any>;
        router_active?: boolean;
        timestamp?: number;
        error?: string;
      }
  );

// Semantic Cache endpoints
export const getCacheHealth = () => api.get('/cache/health').then(r => r.data as any);
export const getCacheAnalytics = () => api.get('/cache/analytics').then(r => r.data as any);
export const clearCache = (pattern?: string, adminToken?: string) =>
  api
    .post(
      '/cache/clear',
      { pattern },
      {
        headers: adminToken ? { 'x-admin-token': adminToken } : undefined,
      }
    )
    .then(r => r.data as any);

export const getCacheStatus = () => api.get('/cache/status').then(r => r.data as any);
export const getCacheReport = () => api.get('/cache/report').then(r => r.data as any);
export const optimizeCache = (targetHitRate: number) =>
  api
    .post('/cache/optimize', null, { params: { target_hit_rate: targetHitRate } })
    .then(r => r.data as any);
export const warmCache = () => api.post('/cache/warm').then(r => r.data as any);

// Router thresholds (admin)
export const setRouterThresholds = (
  params: Partial<{ conf_threshold: number; support_threshold: number; max_cot_tokens: number }>,
  adminToken?: string
) =>
  api
    .post('/admin/router/set-thresholds', params, {
      headers: adminToken ? { 'x-admin-token': adminToken } : undefined,
    })
    .then(r => r.data as { status?: string; current_thresholds?: any; error?: string });

// Swarm status
export const getSwarmStatus = () => api.get('/swarm/status').then(r => r.data as any);
