import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { authService } from '@/services/auth'

export const RegisterPage: React.FC = () => {
  const navigate = useNavigate()
  const [formData, setFormData] = useState({
    username: '',
    email: '',
    password: '',
    confirmPassword: '',
  })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (formData.password !== formData.confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setLoading(true)
    try {
      await authService.register({
        username: formData.username,
        email: formData.email,
        password: formData.password,
      })
      navigate('/login?registered=true')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="surface-shell flex min-h-screen items-center justify-center px-4 py-10">
      <div className="absolute inset-x-0 top-10 flex justify-center">
        <div className="h-44 w-44 rounded-full bg-pink-400/20 blur-3xl" />
      </div>
      <div className="relative w-full max-w-md">
        <div className="card">
          <h1 className="mb-2 text-center text-3xl font-black tracking-tight text-slate-900">Create Account</h1>
          <p className="mb-8 text-center text-sm text-slate-500">Join the dashboard with a polished social-inspired theme.</p>

          {error && <div className="mb-4 rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-rose-700">{error}</div>}

          <form onSubmit={handleSubmit}>
            <div className="mb-4">
              <label className="mb-2 block font-semibold text-slate-700">Username</label>
              <input
                type="text"
                value={formData.username}
                onChange={(e) => setFormData({ ...formData, username: e.target.value })}
                className="w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15"
                minLength={3}
                required
              />
            </div>

            <div className="mb-4">
              <label className="mb-2 block font-semibold text-slate-700">Email</label>
              <input
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                className="w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15"
                required
              />
            </div>

            <div className="mb-4">
              <label className="mb-2 block font-semibold text-slate-700">Password</label>
              <input
                type="password"
                value={formData.password}
                onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                className="w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15"
                minLength={8}
                required
              />
            </div>

            <div className="mb-6">
              <label className="mb-2 block font-semibold text-slate-700">Confirm Password</label>
              <input
                type="password"
                value={formData.confirmPassword}
                onChange={(e) => setFormData({ ...formData, confirmPassword: e.target.value })}
                className="w-full rounded-2xl border border-sky-100 bg-white/90 px-4 py-3 text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-4 focus:ring-sky-500/15"
                minLength={8}
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full btn-primary disabled:opacity-50"
            >
              {loading ? 'Creating account...' : 'Register'}
            </button>
          </form>

          <p className="mt-4 text-center text-slate-500">
            Already have an account?{' '}
            <Link to="/login" className="font-semibold text-sky-700 hover:text-pink-600 hover:underline">
              Login
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
