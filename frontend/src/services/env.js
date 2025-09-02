export function getBackendHttpBase() {
    // Prefer runtime config, then Vite env var, then CRA-style, else same-origin
    const runtime = (typeof window !== 'undefined' ? window.__APP_CONFIG__?.backendUrl : '') || '';
    const vite = import.meta.env?.VITE_BACKEND_URL;
    const react = import.meta.env?.REACT_APP_BACKEND_URL;
    const explicit = (runtime || vite || react || '').trim().replace(/\/$/, '');
    if (explicit)
        return explicit;
    if (typeof window !== 'undefined' && window.location) {
        return window.location.origin;
    }
    // Final fallback
    return '';
}
export function getBackendWsBase() {
    const http = getBackendHttpBase();
    if (http) {
        try {
            const u = new URL(http);
            u.protocol = u.protocol === 'https:' ? 'wss:' : 'ws:';
            return u.origin;
        }
        catch {
            // ignore
        }
    }
    if (typeof window !== 'undefined' && window.location) {
        return (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + window.location.host;
    }
    return 'ws://localhost:8000';
}
