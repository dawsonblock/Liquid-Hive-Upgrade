import axios from 'axios';
import { getBackendHttpBase } from './env';
// If an explicit backend base exists, point axios to it. Otherwise, rely on Vite dev proxy via '/api'.
const httpBase = getBackendHttpBase();
const baseURL = httpBase ? `${httpBase}/api` : '/api';
export const api = axios.create({
    baseURL,
    headers: { 'Content-Type': 'application/json' }
});
export const fetchState = () => api.get('/state').then(r => r.data);
export const postChat = (q) => api.post('/chat?q=' + encodeURIComponent(q)).then(r => r.data);
export const postVision = (form, groundingRequired) => api.post('/vision?grounding_required=' + String(groundingRequired), form, {
    headers: { 'Content-Type': 'multipart/form-data' },
}).then(r => r.data);
export const getApprovals = () => api.get('/approvals').then(r => r.data);
export const approveProposal = (id) => api.post(`/approvals/${id}/approve`).then(r => r.data);
export const denyProposal = (id) => api.post(`/approvals/${id}/deny`).then(r => r.data);
export const getAdaptersState = () => api.get('/adapters/state').then(r => r.data);
export const promoteAdapter = (role) => api.post(`/adapters/promote/${encodeURIComponent(role)}`).then(r => r.data);
export const getGovernor = () => api.get('/config/governor').then(r => r.data);
export const setGovernor = (enabled, force_deepseek_r1) => api.post('/config/governor', { enabled, force_deepseek_r1 }).then(r => r.data);
// Health endpoint to check backend connectivity
export const health = async () => {
    try {
        const res = await api.get('/healthz');
        return { ok: res.status === 200, data: res.data };
    }
    catch (_e) {
        return { ok: false, data: null };
    }
};
export const startTraining = () => api.post('/train').then(r => r.data);
export const previewAutopromote = () => api.get('/autonomy/autopromote/preview').then(r => r.data);
// New secrets health endpoint
export const getSecretsHealth = () => api.get('/secrets/health').then(r => r.data);
// Secrets management helpers
export const secretExists = (name) => api.get(`/secrets/exists`, { params: { name } }).then(r => r.data);
export const setSecret = (name, value, adminToken) => api.post('/secrets/set', { name, value }, {
    headers: adminToken ? { 'x-admin-token': adminToken } : undefined
}).then(r => r.data);
export const reloadRouterSecrets = (adminToken) => api.post('/admin/router/reload-secrets', {}, {
    headers: adminToken ? { 'x-admin-token': adminToken } : undefined
}).then(r => r.data);
// Providers status
export const getProvidersStatus = () => api.get('/providers').then(r => r.data);
