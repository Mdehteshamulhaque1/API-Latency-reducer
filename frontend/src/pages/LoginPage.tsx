import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { authService } from '@/services/auth'
import { useAuthStore } from '@/store'

export const LoginPage: React.FC = () => {
  const navigate = useNavigate()
  const login = useAuthStore((state) => state.login)
  const [formData, setFormData] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await authService.login(formData)
      login(response.access_token, response.refresh_token, { username: formData.username })
      navigate('/dashboard')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="surface-shell flex min-h-screen items-center justify-center px-4 py-10">
      <div className="absolute inset-x-0 top-10 flex justify-center">
        <div className="h-44 w-44 rounded-full bg-sky-400/20 blur-3xl" />
      </div>
      <div className="relative w-full max-w-md">
        <div className="card">
          <div className="mb-8 text-center">
            <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-gradient-to-br from-sky-600 via-blue-600 to-pink-500 text-white shadow-lg shadow-sky-500/25">
              <span className="text-xl font-black">A</span>
            </div>
            <h1 className="text-3xl font-black tracking-tight text-slate-900">API Optimizer</h1>
            <p className="mt-2 text-sm text-slate-500">LinkedIn clarity with Instagram energy</p>
          </div>

          {error && <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="mb-2 block font-semibold text-slate-700">Username</label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15"
                required
              />
            </div>

            <div className="mb-6">
              <label className="mb-2 block font-semibold text-slate-700">Password</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary disabled:opacity-50"
            >
              {loading ? 'Logging in...' : 'Login'}
            </button>
          </form>

          <p className="mt-4 text-center text-slate-500">
            Don't have an account?{' '}
            <a href="/register" className="font-semibold text-sky-700 hover:text-pink-600 hover:underline">
              Register
            </a>
          </p>

          <div className="mt-6 rounded-2xl border border-sky-100 bg-sky-50/80 p-4 text-sm text-slate-700">
            <p className="mb-2 font-semibold text-slate-900">Demo Credentials:</p>
            <p>Username: demo_user</p>
            <p>Password: DemoPassword123!</p>
          </div>
        </div>
      </div>
    </div>
  )
}
