// Centralized API and WebSocket configuration for local dev and cloud production deployments

const rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
export const API_BASE_URL = rawApiUrl.replace(/\/+$/, '');

const rawWsUrl = import.meta.env.VITE_WS_URL || API_BASE_URL.replace(/^http/, 'ws');
export const WS_BASE_URL = rawWsUrl.replace(/\/+$/, '');
