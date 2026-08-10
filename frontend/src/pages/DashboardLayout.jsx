import { useEffect, useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  LayoutDashboard,
  BarChart3,
  ListChecks,
  HeartPulse,
  LogOut,
  Menu,
  X,
  ChevronRight,
  Search,
  Bell,
  WifiOff,
  Wifi,
} from 'lucide-react'
import Logo from '../components/Logo'
import { useAuth } from '../context/AuthContext'
import { LiveBadge } from '../components/dashboard/ui'
import { DashboardDataProvider, useDashboardData } from '../context/DashboardDataContext'

const nav = [
  { to: '/dashboard', label: 'Overview', icon: LayoutDashboard, end: true },
  { to: '/dashboard/analytics', label: 'Analytics', icon: BarChart3 },
  { to: '/dashboard/rules', label: 'Cache rules', icon: ListChecks },
  { to: '/dashboard/health', label: 'API health', icon: HeartPulse },
]

function Sidebar({ open, onClose }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const { live } = useDashboardData(24)

  const content = (
    <div className="flex h-full flex-col bg-white">
      <div className="flex h-18 items-center justify-between border-b border-slate-100 px-6" style={{ height: '4.5rem' }}>
        <NavLink to="/" onClick={onClose}>
          <Logo size={36} />
        </NavLink>
        <button className="rounded-lg p-1.5 text-slate-400 hover:bg-slate-100 lg:hidden" onClick={onClose} aria-label="Close menu">
          <X size={20} />
        </button>
      </div>

      <nav className="flex-1 space-y-1.5 overflow-y-auto scrollbar-thin px-4 py-6">
        <p className="px-3 pb-2 text-[10px] font-bold uppercase tracking-[0.25em] text-slate-400">
          Menu
        </p>
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            end={item.end}
            onClick={onClose}
            className={({ isActive }) =>
              `group flex items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-semibold transition-all ${
                isActive
                  ? 'bg-gradient-to-r from-brand-600 to-violet-600 text-white shadow-lg shadow-brand-600/25'
                  : 'text-slate-600 hover:bg-brand-50 hover:text-brand-700'
              }`
            }
          >
            <item.icon size={18} className="shrink-0" />
            {item.label}
            <ChevronRight size={15} className="ml-auto opacity-40" />
          </NavLink>
        ))}
      </nav>

      <div className="border-t border-slate-100 p-4">
        <button
          onClick={() => { logout(); navigate('/') }}
          className="flex w-full items-center gap-3 rounded-xl px-3.5 py-3 text-sm font-semibold text-slate-500 transition-colors hover:bg-rose-50 hover:text-rose-600"
        >
          <LogOut size={18} />
          Sign out
        </button>
      </div>
    </div>
  )

  return (
    <>
      {/* Desktop */}
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 border-r border-slate-200 lg:block">
        {content}
      </aside>

      {/* Mobile drawer */}
      {open && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute inset-0 bg-slate-950/40 backdrop-blur-sm"
            onClick={onClose}
          />
          <motion.aside
            initial={{ x: '-100%' }}
            animate={{ x: 0 }}
            transition={{ type: 'spring', stiffness: 320, damping: 32 }}
            className="absolute inset-y-0 left-0 w-72 shadow-2xl"
          >
            {content}
          </motion.aside>
        </div>
      )}
    </>
  )
}

export default function DashboardLayout() {
  const [open, setOpen] = useState(false)
  const [scrolled, setScrolled] = useState(false)
  const { user, demoMode } = useAuth()
  const { live } = useDashboardData(24)

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  return (
    <DashboardDataProvider>
      <div className="min-h-screen bg-slate-50">
        <Sidebar open={open} onClose={() => setOpen(false)} />

      <div className="lg:pl-64">
        {/* Topbar */}
        <header
          className={`sticky top-0 z-30 flex h-18 items-center gap-4 border-b transition-all duration-300 ${
            scrolled ? 'glass shadow-sm' : 'bg-slate-50/60 backdrop-blur'
          } px-5 sm:px-8`}
          style={{ height: '4.5rem' }}
        >
          <button
            className="rounded-lg p-2 text-slate-600 hover:bg-slate-200/60 lg:hidden"
            onClick={() => setOpen(true)}
            aria-label="Open menu"
          >
            <Menu size={22} />
          </button>

          <div className="relative hidden max-w-md flex-1 sm:block">
            <Search size={16} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-400" />
            <input
              placeholder="Search endpoints, rules…"
              className="w-full rounded-xl border border-slate-200 bg-white py-2.5 pl-10 pr-4 text-sm outline-none transition-all focus:border-brand-500 focus:ring-4 focus:ring-brand-500/10"
            />
          </div>

          <div className="ml-auto flex items-center gap-3">
            <span className="hidden items-center gap-1.5 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-semibold text-slate-500 sm:inline-flex">
              {live ? <Wifi size={13} className="text-emerald-500" /> : <WifiOff size={13} className="text-amber-500" />}
              {live ? 'Backend connected' : 'Demo mode'}
            </span>
            <LiveBadge live={live} />
            <button className="relative rounded-xl border border-slate-200 bg-white p-2.5 text-slate-500 transition-colors hover:border-brand-300 hover:text-brand-600">
              <Bell size={17} />
              <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full bg-rose-500 ring-2 ring-white" />
            </button>
            <div className="flex items-center gap-2.5 rounded-xl border border-slate-200 bg-white py-1.5 pl-1.5 pr-3.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-brand-500 to-violet-600 text-xs font-bold text-white">
                {(user?.username || 'U').slice(0, 1).toUpperCase()}
              </span>
              <div className="hidden sm:block">
                <p className="text-xs font-bold text-slate-800">{user?.username || 'User'}</p>
                <p className="text-[10px] text-slate-400">{demoMode ? 'Demo · viewer' : 'viewer'}</p>
              </div>
            </div>
          </div>
        </header>

        <main className="px-5 py-8 sm:px-8">
          <Outlet />
        </main>
      </div>
      </div>
    </DashboardDataProvider>
  )
}
