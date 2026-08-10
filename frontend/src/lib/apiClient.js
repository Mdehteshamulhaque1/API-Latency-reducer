import api from './axios'
import { mockSummary, mockRules, mockHealth } from './mockData'

async function safe(fn, fallback) {
  try {
    const data = await fn()
    return { data, live: true }
  } catch (err) {
    const reason = err?.response?.status ?? err?.message ?? 'unknown'
    console.warn(`[API Optimizer] Backend request failed (${reason}); showing demo data.`)
    return { data: fallback, live: false }
  }
}

export const apiClient = {
  login: (username, password) => api.post('/auth/login', { username, password }),

  register: (payload) =>
    api.post('/auth/register', {
      username: payload.username,
      email: payload.email,
      password: payload.password,
      role: payload.role || 'viewer',
    }),

  refresh: (refreshToken) => api.post('/auth/refresh', { refresh_token: refreshToken }),

  summary: (hours = 24) => safe(() => api.get(`/analytics/summary?hours=${hours}`), mockSummary(hours)),

  benchmark: (hours = 24) =>
    safe(
      () => api.get(`/analytics/benchmark?hours=${hours}`),
      mockSummary(hours).benchmark
    ),

  slowEndpoints: (hours = 24, limit = 10) =>
    safe(
      () => api.get(`/analytics/slow-endpoints?hours=${hours}&limit=${limit}`),
      mockSummary(hours).slow_endpoint_ranking
    ),

  suggestions: (hours = 24) =>
    safe(() => api.get(`/analytics/suggestions?hours=${hours}`), mockSummary(hours).optimization_suggestions),

  rules: () => safe(() => api.get('/rules'), mockRules),

  createRule: (rule) =>
    safe(async () => {
      const created = await api.post('/rules', rule)
      return created
    }, { ...rule, id: Date.now(), created_at: new Date().toISOString(), updated_at: new Date().toISOString() }),

  updateRule: (id, rule) => safe(() => api.put(`/rules/${id}`, rule), { id, ...rule }),

  deleteRule: (id) => safe(() => api.delete(`/rules/${id}`), { ok: true }),

  health: () => safe(() => api.get('/health'), mockHealth),
}

export function isDemo(data) {
  return data && data.live === false
}
