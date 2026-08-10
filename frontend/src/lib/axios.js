import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 8000,
})

const TOKEN_KEY = 'api_access_token'
const REFRESH_TOKEN_KEY = 'api_refresh_token'

let refreshPromise = null

async function performRefresh() {
  const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
  if (!refreshToken) throw new Error('No refresh token available')

  const { data } = await axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken })

  if (!data?.access_token) throw new Error('Refresh response missing access token')

  localStorage.setItem(TOKEN_KEY, data.access_token)
  if (data.refresh_token) localStorage.setItem(REFRESH_TOKEN_KEY, data.refresh_token)
  return data.access_token
}

function forceLogout() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem('api_user')
  window.dispatchEvent(new CustomEvent('api:auth-expired'))
}

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response.data,
  async (error) => {
    const original = error.config

    // Refresh request itself, or a request already retried with a fresh token
    // that still got rejected — the session is invalid, log out.
    if (error.response?.status !== 401 || !original) {
      return Promise.reject(error)
    }
    if (original._retry || (original.url && original.url.includes('/auth/refresh'))) {
      forceLogout()
      return Promise.reject(error)
    }

    try {
      // Single-flight: only one refresh request runs at a time.
      refreshPromise = refreshPromise || performRefresh()
      const accessToken = await refreshPromise
      refreshPromise = null

      original._retry = true
      original.headers.Authorization = `Bearer ${accessToken}`
      return api(original)
    } catch (refreshError) {
      refreshPromise = null
      forceLogout()
      return Promise.reject(refreshError)
    }
  }
)

export default api
