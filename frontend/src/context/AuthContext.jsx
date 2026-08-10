import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { apiClient } from '../lib/apiClient'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem('api_user')
      return raw ? JSON.parse(raw) : null
    } catch {
      return null
    }
  })
  const [token, setToken] = useState(() => localStorage.getItem('api_access_token') || null)
  const [demoMode, setDemoMode] = useState(() => localStorage.getItem('api_demo') === '1')

  const login = useCallback(async (username, password) => {
    const res = await apiClient.login(username, password)
    const accessToken = res.access_token
    const refreshToken = res.refresh_token
    localStorage.setItem('api_access_token', accessToken)
    localStorage.setItem('api_refresh_token', refreshToken)
    localStorage.setItem('api_demo', '0')
    localStorage.setItem(
      'api_user',
      JSON.stringify({ username, role: 'user', demo: false })
    )
    setToken(accessToken)
    setDemoMode(false)
    setUser({ username, role: 'user', demo: false })
    return { token: accessToken, user: { username } }
  }, [])

  const enterDemo = useCallback(() => {
    localStorage.setItem('api_demo', '1')
    localStorage.setItem('api_user', JSON.stringify({ username: 'demo', role: 'viewer', demo: true }))
    setDemoMode(true)
    setUser({ username: 'demo', role: 'viewer', demo: true })
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem('api_access_token')
    localStorage.removeItem('api_refresh_token')
    localStorage.removeItem('api_demo')
    localStorage.removeItem('api_user')
    setToken(null)
    setDemoMode(false)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, token, demoMode, isAuthenticated: Boolean(token) || demoMode, login, enterDemo, logout }),
    [user, token, demoMode, login, enterDemo, logout]
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
