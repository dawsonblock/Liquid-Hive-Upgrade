import axios from 'axios';

// Always use backend URL from env (must include /api prefix per ingress rules)
const BACKEND_BASE = (typeof window !== 'undefined' && import.meta && import.meta.env && import.meta.env.REACT_APP_BACKEND_URL)
  || (typeof process !== 'undefined' && process.env && process.env.REACT_APP_BACKEND_URL);

if (!BACKEND_BASE) {
  // Do not hardcode fallbacks per platform rules
  // Expose a clear error to help diagnose misconfiguration
  // eslint-disable-next-line no-console
  console.error('REACT_APP_BACKEND_URL is not set. API calls will fail.');
}

export const api = axios.create({
  baseURL: BACKEND_BASE,
  headers: { 'Content-Type': 'application/json' },
});

export const fetchState = () => api.get('/state').then(r => r.data);
export const postChat = (q) => api.post('/chat?q=' + encodeURIComponent(q)).then(r => r.data);
export const postVision = (form, groundingRequired) =>
  api.post('/vision?grounding_required=' + String(groundingRequired), form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
export const getApprovals = () => api.get('/approvals').then(r => r.data);
export const approveProposal = (id) => api.post(`/approvals/${id}/approve`).then(r => r.data);
export const denyProposal = (id) => api.post(`/approvals/${id}/deny`).then(r => r.data);
export const getAdaptersState = () => api.get('/adapters/state').then(r => r.data);
export const promoteAdapter = (role) => api.post(`/adapters/promote/${encodeURIComponent(role)}`).then(r => r.data);
export const getGovernor = () => api.get('/config/governor').then(r => r.data);
export const setGovernor = (enabled, force_gpt4o) => api.post('/config/governor', { enabled, force_gpt4o }).then(r => r.data);
export const startTraining = () => api.post('/train').then(r => r.data);