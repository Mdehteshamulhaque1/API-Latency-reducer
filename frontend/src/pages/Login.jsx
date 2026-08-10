import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Zap,
  ShieldCheck,
  BarChart3,
  Lock,
  User as UserIcon,
  ArrowRight,
  Eye,
  EyeOff,
  Loader2,
  FlaskConical,
  AlertCircle,
} from 'lucide-react'
import Logo from '../components/Logo'
import Button from '../components/Button'
import { useAuth } from '../context/AuthContext'

const perks = [
  { icon: Zap, text: 'Redis-backed caching for 2–5× faster responses' },
  { icon: ShieldCheck, text: 'JWT auth with strict token-type validation' },
  { icon: BarChart3, text: 'Real-time analytics with p95 / p99 latency' },
]

export default function Login() {
  const { login, enterDemo } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/dashboard')
    } catch (err) {
      const detail =
        err?.response?.data?.detail || 'Login failed. Is the backend running on port 8000?'
      setError(detail)
    } finally {
      setLoading(false)
    }
  }

  const handleDemo = () => {
    enterDemo()
    navigate('/dashboard')
  }

  return (
    <div className="grid min-h-screen lg:grid-cols-2">
      {/* ------- Form side ------- */}
      <div className="relative flex items-center justify-center bg-white px-6 py-14">
        <div className="bg-dots absolute inset-0 opacity-40" aria-hidden />
        <div className="relative w-full max-w-md">
          <motion.div initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.6 }}>
            <Logo size={44} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.1 }}
          >
            <h1 className="font-display mt-10 text-3xl font-bold tracking-tight text-slate-900">
              Welcome back
            </h1>
            <p className="mt-2 text-sm text-slate-500">
              Sign in to your dashboard. Use your registered username and password.
            </p>
          </motion.div>

          <motion.form
            initial={{ opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.6, delay: 0.2 }}
            onSubmit={handleSubmit}
            className="mt-8 space-y-5"
          >
            {error && (
              <motion.div
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-start gap-2.5 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700"
              >
                <AlertCircle size={17} className="mt-0.5 shrink-0" />
                {error}
              </motion.div>
            )}

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700" htmlFor="username">
                Username
              </label>
              <div className="group relative">
                <UserIcon
                  size={17}
                  className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-brand-500"
                />
                <input
                  id="username"
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                  autoComplete="username"
                  placeholder="e.g. admin"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-3 pl-10 pr-4 text-sm text-slate-800 outline-none transition-all focus:border-brand-500 focus:bg-white focus:ring-4 focus:ring-brand-500/10"
                />
              </div>
            </div>

            <div>
              <label className="mb-1.5 block text-sm font-semibold text-slate-700" htmlFor="password">
                Password
              </label>
              <div className="group relative">
                <Lock
                  size={17}
                  className="pointer-events-none absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400 transition-colors group-focus-within:text-brand-500"
                />
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="w-full rounded-xl border border-slate-200 bg-slate-50/60 py-3 pl-10 pr-11 text-sm text-slate-800 outline-none transition-all focus:border-brand-500 focus:bg-white focus:ring-4 focus:ring-brand-500/10"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 transition-colors hover:text-brand-600"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between text-sm">
              <label className="flex cursor-pointer items-center gap-2 text-slate-600">
                <input type="checkbox" className="h-4 w-4 rounded border-slate-300 accent-brand-600" />
                Remember me
              </label>
              <a href="#" className="font-semibold text-brand-600 hover:text-brand-700">
                Forgot password?
              </a>
            </div>

            <Button type="submit" size="lg" className="w-full" disabled={loading} icon={loading ? Loader2 : ArrowRight}>
              {loading ? 'Signing in…' : 'Sign in'}
            </Button>
          </motion.form>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.35 }}
            className="mt-6 flex items-center gap-3"
          >
            <span className="divider-gradient flex-1" />
            <span className="text-xs font-medium uppercase tracking-widest text-slate-400">or</span>
            <span className="divider-gradient flex-1" />
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.4 }}
            className="mt-6"
          >
            <Button variant="secondary" size="lg" className="w-full" onClick={handleDemo} icon={FlaskConical}>
              Explore with demo data
            </Button>
            <p className="mt-3 text-center text-xs text-slate-400">
              No backend? Demo mode loads realistic sample analytics.
            </p>
          </motion.div>
        </div>
      </div>

      {/* ------- Showcase side ------- */}
      <div className="relative hidden overflow-hidden bg-slate-950 lg:block">
        <div className="bg-grid-slate absolute inset-0 opacity-20" aria-hidden />
        <div
          className="absolute inset-0"
          aria-hidden
          style={{
            background:
              'radial-gradient(80% 60% at 20% 20%, rgba(99,102,241,0.35), transparent 60%), radial-gradient(70% 50% at 85% 85%, rgba(6,182,212,0.3), transparent 60%)',
          }}
        />
        <motion.div
          animate={{ y: [0, -18, 0] }}
          transition={{ duration: 9, repeat: Infinity, ease: 'easeInOut' }}
          className="relative flex h-full flex-col justify-center px-14"
        >
          <motion.div
            className="flex justify-center"
            animate={{ rotate: [0, 4, 0, -4, 0] }}
            transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
          >
            <Logo size={96} showText={false} />
          </motion.div>

          <h2 className="font-display mt-10 text-center text-4xl font-bold text-white">
            The dashboard your API <span className="shimmer-text">deserves</span>
          </h2>
          <p className="mx-auto mt-4 max-w-md text-center text-sm leading-relaxed text-slate-400">
            One login gives you request analytics, cache metrics, slow-endpoint ranking,
            and optimization suggestions — all updated in real time.
          </p>

          <div className="mt-12 space-y-5">
            {perks.map((p, i) => (
              <motion.div
                key={p.text}
                initial={{ opacity: 0, x: 40 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.5 + i * 0.15 }}
                className="glass-dark flex items-center gap-4 rounded-2xl border border-white/10 px-5 py-4"
              >
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-gradient-to-br from-brand-500 to-accent-500 text-white shadow-lg">
                  <p.icon size={18} />
                </span>
                <p className="text-sm font-medium text-slate-200">{p.text}</p>
              </motion.div>
            ))}
          </div>

          <div className="mt-12 flex items-center justify-center gap-2 text-xs text-slate-500">
            <Lock size={13} />
            Secured with JWT token-type validation
          </div>
        </motion.div>
      </div>
    </div>
  )
}
