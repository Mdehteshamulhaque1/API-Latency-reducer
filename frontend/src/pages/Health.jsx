import { motion } from 'framer-motion'
import {
  HeartPulse,
  Database,
  Server,
  RefreshCw,
  Cpu,
  Container,
  KeyRound,
  Gauge,
  CircleCheck,
  CircleX,
} from 'lucide-react'
import { useDashboardData } from '../context/DashboardDataContext'
import { Card, PageHeader, Badge, LiveBadge, LoadingBlock } from '../components/dashboard/ui'

function StatusPill({ healthy }) {
  return healthy ? (
    <span className="inline-flex items-center gap-1.5 text-emerald-600">
      <CircleCheck size={16} />
      <span className="text-sm font-bold">Healthy</span>
    </span>
  ) : (
    <span className="inline-flex items-center gap-1.5 text-rose-600">
      <CircleX size={16} />
      <span className="text-sm font-bold">Degraded</span>
    </span>
  )
}

const stack = [
  { icon: Server, label: 'Backend', value: 'FastAPI 0.104', color: 'from-brand-500 to-violet-500' },
  { icon: Database, label: 'Database', value: 'MySQL / SQLite', color: 'from-accent-500 to-cyan-500' },
  { icon: Container, label: 'Cache', value: 'Redis 7', color: 'from-rose-500 to-orange-500' },
  { icon: KeyRound, label: 'Auth', value: 'JWT + bcrypt', color: 'from-emerald-500 to-teal-500' },
  { icon: Cpu, label: 'ORM', value: 'SQLAlchemy 2.0', color: 'from-violet-500 to-fuchsia-500' },
  { icon: Gauge, label: 'Limiter', value: 'Token bucket', color: 'from-sky-500 to-blue-500' },
]

export default function Health() {
  const { loading, health, live, refresh } = useDashboardData()

  if (loading) return <LoadingBlock label="Checking service health…" />

  const dbHealthy = health?.database === 'healthy'
  const redisHealthy = health?.redis === 'healthy'
  const overall = live && dbHealthy && redisHealthy ? 'healthy' : 'degraded'

  return (
    <div>
      <PageHeader
        title="API health"
        description="Live status of the backend services powering this dashboard."
        actions={
          <button
            onClick={refresh}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 transition-colors hover:border-brand-400 hover:text-brand-600"
          >
            <RefreshCw size={15} /> Re-check
          </button>
        }
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Overall status */}
        <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} className="lg:col-span-1">
          <Card className="relative h-full overflow-hidden">
            <div
              className={`pointer-events-none absolute -right-12 -top-12 h-40 w-40 rounded-full bg-gradient-to-br ${
                overall === 'healthy' ? 'from-emerald-500 to-teal-500' : 'from-rose-500 to-orange-500'
              } opacity-10 blur-2xl`}
            />
            <div className="flex items-center justify-between">
              <h3 className="font-display text-lg font-bold text-slate-900">Overall status</h3>
              <LiveBadge live={live} />
            </div>

            <div className="mt-8 flex flex-col items-center">
              <div className="relative flex h-28 w-28 items-center justify-center">
                <span
                  className={`absolute inset-0 animate-pulse-ring rounded-full border-2 ${
                    overall === 'healthy' ? 'border-emerald-400/50' : 'border-rose-400/50'
                  }`}
                />
                <span
                  className={`flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br ${
                    overall === 'healthy'
                      ? 'from-emerald-500 to-teal-500'
                      : 'from-rose-500 to-orange-500'
                  } text-white shadow-xl`}
                >
                  <HeartPulse size={34} />
                </span>
              </div>
              <p className="font-display mt-5 text-2xl font-bold capitalize text-slate-900">{overall}</p>
              <p className="mt-1 text-xs text-slate-400">API Optimizer v{health?.version || '1.0.0'}</p>
            </div>

            <div className="mt-8 space-y-3">
              {[
                { label: 'Database', healthy: dbHealthy },
                { label: 'Redis cache', healthy: redisHealthy },
              ].map((s) => (
                <div key={s.label} className="flex items-center justify-between rounded-xl border border-slate-100 bg-slate-50/60 px-4 py-3">
                  <span className="flex items-center gap-2 text-sm font-semibold text-slate-700">
                    <span className={`h-2 w-2 rounded-full ${s.healthy ? 'bg-emerald-500' : 'bg-rose-500'}`} />
                    {s.label}
                  </span>
                  <StatusPill healthy={s.healthy} />
                </div>
              ))}
            </div>
          </Card>
        </motion.div>

        {/* Service details */}
        <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="lg:col-span-2">
          <Card className="h-full">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg font-bold text-slate-900">Service details</h3>
                <p className="text-xs text-slate-400">Raw health payload from the backend</p>
              </div>
              <Badge tone="green">
                <Database size={12} /> {health?.database}
              </Badge>
            </div>

            <div className="mt-5 overflow-hidden rounded-xl border border-slate-100 bg-slate-950 font-mono text-xs leading-relaxed">
              <div className="flex items-center gap-2 border-b border-white/10 px-4 py-2.5 text-slate-400">
                <span className="h-2.5 w-2.5 rounded-full bg-rose-400" />
                <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
                <span className="h-2.5 w-2.5 rounded-full bg-emerald-400" />
                <span className="ml-2">GET /api/v1/health</span>
              </div>
              <pre className="overflow-x-auto scrollbar-thin p-4 text-emerald-300">
{`{
  "status": "${health?.status}",
  "version": "${health?.version}",
  "database": "${health?.database}",
  "redis": "${health?.redis}"
}`}
              </pre>
            </div>

            <h3 className="font-display mt-8 text-lg font-bold text-slate-900">Powered by</h3>
            <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {stack.map((s, i) => (
                <motion.div
                  key={s.label}
                  initial={{ opacity: 0, y: 14 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.2 + i * 0.06 }}
                  className="flex items-center gap-3 rounded-xl border border-slate-100 p-4 transition-colors hover:border-brand-200 hover:bg-brand-50/30"
                >
                  <span className={`flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br ${s.color} text-white shadow-md`}>
                    <s.icon size={18} />
                  </span>
                  <div>
                    <p className="text-sm font-bold text-slate-800">{s.label}</p>
                    <p className="text-xs text-slate-400">{s.value}</p>
                  </div>
                </motion.div>
              ))}
            </div>
          </Card>
        </motion.div>
      </div>
    </div>
  )
}
