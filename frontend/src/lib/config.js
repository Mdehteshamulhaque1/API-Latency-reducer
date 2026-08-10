export const API_BASE_URL = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')
export const DOCS_URL = import.meta.env.VITE_DOCS_URL || `${API_BASE_URL.replace(/\/api\/v1$/, '')}/docs`
