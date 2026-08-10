import { motion } from 'framer-motion'
import { Loader2 } from 'lucide-react'

export function Card({ children, className = '', pad = true }) {
  return (
    <div className={`card ${pad ? 'p-5 sm:p-6' : ''} ${className}`}>{children}</div>
  )
}

export function StatCard({ label, value, sub, icon: Icon, gradient = 'from-brand-500 to-violet-500', delay = 0, badge }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 18 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, delay }}
      whileHover={{ y: -4 }}
      className="card card-hover relative overflow-hidden p-5"
    >
      <div
        className={`pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full bg-gradient-to-br ${gradient} opacity-10 blur-xl`}
      />
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold uppercase tracking-widest text-slate-400">{label}</p>
        <span
          className={`flex h-9 w-9 items-center justify-center rounded-xl bg-gradient-to-br ${gradient} text-white shadow-md`}
        >
          <Icon size={17} />
        </span>
      </div>
      <p className="font-display mt-3 text-2xl font-bold text-slate-900 sm:text-3xl">{value}</p>
      {sub && <p className="mt-1.5 text-xs text-slate-400">{sub}</p>}
      {badge}
    </motion.div>
  )
}

export function PageHeader({ title, description, actions }) {
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
      <div>
        <h1 className="font-display text-2xl font-bold tracking-tight text-slate-900 sm:text-3xl">
          {title}
        </h1>
        {description && <p className="mt-1 text-sm text-slate-500">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  )
}

export function Badge({ children, tone = 'slate' }) {
  const tones = {
    slate: 'bg-slate-100 text-slate-600',
    green: 'bg-emerald-50 text-emerald-600',
    red: 'bg-rose-50 text-rose-600',
    brand: 'bg-brand-50 text-brand-600',
    amber: 'bg-amber-50 text-amber-600',
  }
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

export function LiveBadge({ live }) {
  return live ? (
    <Badge tone="green">
      <span className="relative flex h-1.5 w-1.5">
        <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
        <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-emerald-500" />
      </span>
      Live
    </Badge>
  ) : (
    <Badge tone="amber">
      <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
      Demo data
    </Badge>
  )
}

export function Skeleton({ className = '' }) {
  return (
    <div className={`animate-pulse rounded-xl bg-slate-100 ${className}`} aria-hidden />
  )
}

export function LoadingBlock({ label = 'Loading…' }) {
  return (
    <div className="flex items-center justify-center gap-3 py-16 text-sm text-slate-400">
      <Loader2 size={18} className="animate-spin text-brand-500" />
      {label}
    </div>
  )
}
