import apiClient from './api'

export interface User {
  id: number
  username: string
  email: string
  role: string
  is_active: boolean
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface RegisterData {
  username: string
  email: string
  password: string
}

export interface AuthResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export const authService = {
  register: async (data: RegisterData) => {
    const response = await apiClient.post<User>('/api/v1/auth/register', data)
    return response.data
  },

  login: async (credentials: LoginCredentials) => {
    const response = await apiClient.post<AuthResponse>('/api/v1/auth/login', credentials)
    return response.data
  },

  refresh: async (refreshToken: string) => {
    const response = await apiClient.post<AuthResponse>('/api/v1/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },
}
