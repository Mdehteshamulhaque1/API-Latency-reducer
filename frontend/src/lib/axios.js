import axios from 'axios'

const api = axios.create({
  baseURL: '/api/v1',
  timeout: 8000,
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('api_access_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (response) => response.data,
  (error) => Promise.reject(error)
)

export default api
