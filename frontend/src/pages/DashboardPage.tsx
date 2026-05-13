import React, { useState } from 'react'
import { useQuery } from 'react-query'
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { analyticsService } from '@/services/api-services'
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  Clock3,
  DatabaseZap,
  Gauge,
  RefreshCcw,
  ShieldAlert,
  Sparkles,
  TrendingDown,
  TrendingUp,
  Zap,
} from 'lucide-react'

const COLORS = ['#0a66c2', '#f44786', '#8b5cf6', '#f97316']
const RANGE_OPTIONS = [
  { label: '1H', value: 1 },
  { label: '6H', value: 6 },
  { label: '24H', value: 24 },
  { label: '7D', value: 168 },
]

export const DashboardPage: React.FC = () => {
  const [hours, setHours] = useState(24)

  const { data: analytics, isLoading, isFetching, refetch } = useQuery(
    ['analytics', hours],
    () => analyticsService.getSummary(hours),
    { refetchInterval: 15000 }
  )

  if (isLoading) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center">
        <div className="flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-900/70 px-5 py-4 text-slate-200 shadow-xl backdrop-blur">
          <RefreshCcw className="h-5 w-5 animate-spin text-sky-400" />
          Loading analytics...
        </div>
      </div>
    )
  }

  if (!analytics) {
    return <div className="rounded-2xl border border-pink-500/20 bg-pink-500/10 p-6 text-pink-100">No analytics data available yet.</div>
  }

  const cacheData = [
    { name: 'Hit', value: analytics.cache_hit_rate },
    { name: 'Miss', value: analytics.cache_miss_rate },
  ]

  const latencySeries = analytics.latency_series.map((point) => ({
    name: point.timestamp.slice(11, 16),
    latency: point.avg_response_time_ms,
    requests: point.request_count,
    errors: point.error_count,
  }))

  const endpointSeries = analytics.top_endpoints.slice(0, 6).map((endpoint) => ({
    name: endpoint.endpoint.split('/').filter(Boolean).slice(-1)[0] || 'root',
    requests: endpoint.count,
    latency: endpoint.avg_time,
    errors: endpoint.errors,
  }))

  const benchmark = analytics.benchmark
  const slowEndpoints = analytics.slow_endpoints.slice(0, 5)

  return (
    <div className="relative overflow-hidden rounded-[2rem] border border-white/10 bg-slate-950 text-slate-100 shadow-2xl">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,_rgba(10,102,194,0.18),_transparent_32%),radial-gradient(circle_at_top_right,_rgba(244,71,134,0.16),_transparent_28%),linear-gradient(180deg,rgba(15,23,42,0.94),rgba(2,6,23,0.98))]" />
      <div className="relative space-y-8 p-6 sm:p-8 lg:p-10">
        <header className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-sky-400/20 bg-sky-400/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-sky-200">
              <Activity className="h-3.5 w-3.5" />
              Real-time optimization control room
            </div>
            <div>
              <h1 className="text-3xl font-black tracking-tight text-white sm:text-4xl">API Optimizer Dashboard</h1>
              <p className="mt-2 max-w-3xl text-sm text-slate-300 sm:text-base">
                Live latency analytics, cache telemetry, request health, and optimization hints for the current sample window.
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            <div className="inline-flex items-center gap-2 rounded-full border border-emerald-400/20 bg-emerald-400/10 px-3 py-2 text-sm text-emerald-100">
              <span className={`h-2.5 w-2.5 rounded-full ${isFetching ? 'animate-pulse bg-amber-400' : 'bg-emerald-400'}`} />
              {isFetching ? 'Refreshing' : 'Live'}
            </div>
            <button
              onClick={() => refetch()}
              className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm font-medium text-slate-100 transition hover:bg-white/10"
            >
              <RefreshCcw className="h-4 w-4" />
              Refresh
            </button>
            <div className="flex rounded-full border border-white/10 bg-white/5 p-1">
              {RANGE_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setHours(option.value)}
                  className={`rounded-full px-3 py-1.5 text-sm font-semibold transition ${
                    hours === option.value ? 'bg-pink-500 text-white shadow-lg' : 'text-slate-200 hover:bg-white/5'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
          <StatCard title="Requests" value={analytics.total_requests.toLocaleString()} icon={<Zap className="h-5 w-5" />} accent="cyan" description={`~${analytics.request_rate_per_minute.toFixed(1)} req/min`} />
          <StatCard title="Avg latency" value={`${analytics.avg_response_time_ms.toFixed(0)}ms`} icon={<Clock3 className="h-5 w-5" />} accent="orange" description={`Slowest ${analytics.slowest_response_time_ms?.toFixed(0) ?? 0}ms`} />
          <StatCard title="Cache hit" value={`${analytics.cache_hit_rate.toFixed(1)}%`} icon={<DatabaseZap className="h-5 w-5" />} accent="emerald" description={`${analytics.cache_miss_rate.toFixed(1)}% misses`} />
          <StatCard title="Error rate" value={`${analytics.error_rate.toFixed(2)}%`} icon={<AlertTriangle className="h-5 w-5" />} accent="rose" description={`${analytics.total_errors} failed requests`} />
          <StatCard title="Slow endpoints" value={slowEndpoints.length.toString()} icon={<Gauge className="h-5 w-5" />} accent="violet" description="Needs attention" />
          <StatCard title="Insights" value={analytics.optimization_suggestions.length.toString()} icon={<Sparkles className="h-5 w-5" />} accent="amber" description="Actionable recommendations" />
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.5fr_1fr]">
          <PanelCard title="Latency trend" subtitle="Average response time across the sampled window" icon={<TrendingUp className="h-4 w-4" />}>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={latencySeries}>
                  <defs>
                    <linearGradient id="latencyGradient" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#22d3ee" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="#22d3ee" stopOpacity={0.02} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                  <XAxis dataKey="name" stroke="#94a3b8" tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: '#020617', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 16 }} />
                  <Area type="monotone" dataKey="latency" stroke="#22d3ee" fill="url(#latencyGradient)" strokeWidth={2.5} />
                  <Line type="monotone" dataKey="requests" stroke="#f97316" strokeWidth={2} dot={false} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </PanelCard>

          <PanelCard title="Cache health" subtitle="Hit versus miss distribution" icon={<DatabaseZap className="h-4 w-4" />}>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={cacheData} cx="50%" cy="50%" innerRadius={72} outerRadius={110} paddingAngle={6} dataKey="value">
                    {cacheData.map((_, index) => (
                      <Cell key={index} fill={COLORS[index]} />
                    ))}
                  </Pie>
                  <Tooltip contentStyle={{ background: '#020617', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 16 }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="mt-4 grid grid-cols-2 gap-3 text-sm text-slate-300">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                <div className="text-slate-400">Cache hits</div>
                <div className="mt-1 text-xl font-bold text-white">{analytics.cache_hit_rate.toFixed(1)}%</div>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-3">
                <div className="text-slate-400">Cache misses</div>
                <div className="mt-1 text-xl font-bold text-white">{analytics.cache_miss_rate.toFixed(1)}%</div>
              </div>
            </div>
          </PanelCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.25fr_0.95fr]">
          <PanelCard title="Endpoint pressure" subtitle="Top endpoints by traffic and latency" icon={<ArrowUpRight className="h-4 w-4" />}>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={endpointSeries}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(148,163,184,0.18)" />
                  <XAxis dataKey="name" stroke="#94a3b8" tickLine={false} axisLine={false} />
                  <YAxis stroke="#94a3b8" tickLine={false} axisLine={false} />
                  <Tooltip contentStyle={{ background: '#020617', border: '1px solid rgba(255,255,255,0.12)', borderRadius: 16 }} />
                  <Bar dataKey="requests" fill="#38bdf8" radius={[8, 8, 0, 0]} />
                  <Bar dataKey="latency" fill="#f97316" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </PanelCard>

          <PanelCard title="Benchmark snapshot" subtitle="Before/after comparison for the sampled window" icon={<TrendingDown className="h-4 w-4" />}>
            {benchmark ? (
              <div className="space-y-4">
                <div className="grid gap-3 sm:grid-cols-2">
                  <MetricStrip label="Baseline" value={`${benchmark.baseline_avg_response_time_ms.toFixed(1)}ms`} />
                  <MetricStrip label="Optimized" value={`${benchmark.optimized_avg_response_time_ms.toFixed(1)}ms`} />
                </div>
                <div className="rounded-2xl border border-emerald-400/20 bg-emerald-400/10 p-4">
                  <div className="text-sm text-emerald-100/80">Improvement</div>
                  <div className="mt-1 text-3xl font-black text-white">{benchmark.improvement_percent.toFixed(1)}%</div>
                  <div className="mt-2 text-sm text-emerald-100/80">{benchmark.sample_size} requests sampled</div>
                </div>
                <div className="space-y-3 text-sm text-slate-300">
                  <div>
                    <div className="text-slate-500">Before window</div>
                    <div className="mt-1 text-slate-100">{benchmark.before_window}</div>
                  </div>
                  <div>
                    <div className="text-slate-500">After window</div>
                    <div className="mt-1 text-slate-100">{benchmark.after_window}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-slate-300">No benchmark data available yet.</div>
            )}
          </PanelCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
          <PanelCard title="Optimization suggestions" subtitle="Heuristics derived from request patterns" icon={<Sparkles className="h-4 w-4" />}>
            <div className="space-y-3">
              {analytics.optimization_suggestions.map((suggestion) => (
                <SuggestionCard key={suggestion.title + suggestion.action} suggestion={suggestion} />
              ))}
            </div>
          </PanelCard>

          <PanelCard title="Slow endpoints" subtitle="Routes that need attention" icon={<ShieldAlert className="h-4 w-4" />}>
            <div className="space-y-3">
              {slowEndpoints.map((endpoint) => (
                <div key={endpoint.endpoint} className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="flex items-center justify-between gap-4">
                    <div>
                      <div className="font-semibold text-white">{endpoint.endpoint}</div>
                      <div className="mt-1 text-sm text-slate-400">{endpoint.count} requests, {endpoint.errors} errors</div>
                    </div>
                    <div className="rounded-full bg-rose-500/15 px-3 py-1 text-sm font-semibold text-rose-200">
                      {endpoint.avg_time.toFixed(0)}ms
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </PanelCard>
        </section>

        <section className="grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
          <PanelCard title="Recent requests" subtitle="Latest request telemetry from the sampled window" icon={<Activity className="h-4 w-4" />}>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="border-b border-white/10 text-left text-slate-400">
                    <th className="py-3 pr-4 font-medium">Endpoint</th>
                    <th className="py-3 pr-4 font-medium">Method</th>
                    <th className="py-3 pr-4 font-medium">Status</th>
                    <th className="py-3 pr-4 font-medium">Latency</th>
                    <th className="py-3 pr-4 font-medium">Cache</th>
                  </tr>
                </thead>
                <tbody>
                  {analytics.recent_requests.map((request) => (
                    <tr key={`${request.endpoint}-${request.created_at}`} className="border-b border-white/5 text-slate-200">
                      <td className="py-3 pr-4">{request.endpoint}</td>
                      <td className="py-3 pr-4">
                        <span className="rounded-full bg-cyan-400/10 px-2.5 py-1 text-xs font-semibold text-cyan-200">{request.method}</span>
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${request.status_code >= 400 ? 'bg-rose-500/15 text-rose-200' : 'bg-emerald-500/15 text-emerald-200'}`}>
                          {request.status_code}
                        </span>
                      </td>
                      <td className="py-3 pr-4">{request.response_time_ms.toFixed(1)}ms</td>
                      <td className="py-3 pr-4">
                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${request.cache_hit ? 'bg-emerald-500/15 text-emerald-200' : 'bg-white/10 text-slate-200'}`}>
                          {request.cache_hit ? 'Hit' : 'Miss'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </PanelCard>

          <PanelCard title="System summary" subtitle="Current operational posture" icon={<Gauge className="h-4 w-4" />}>
            <div className="space-y-3 text-sm text-slate-300">
              <InfoRow label="Window" value={`${hours}h`} />
              <InfoRow label="Slowest endpoint" value={analytics.slowest_endpoint ?? 'n/a'} />
              <InfoRow label="Slowest latency" value={`${analytics.slowest_response_time_ms?.toFixed(1) ?? '0.0'}ms`} />
              <InfoRow label="Request rate" value={`~${analytics.request_rate_per_minute.toFixed(1)}/min`} />
              <InfoRow label="Error count" value={analytics.total_errors.toString()} />
            </div>
          </PanelCard>
        </section>
      </div>
    </div>
  )
}

interface StatCardProps {
  title: string
  value: string
  icon: React.ReactNode
  accent: 'cyan' | 'orange' | 'emerald' | 'rose' | 'violet' | 'amber'
  description: string
}

const StatCard: React.FC<StatCardProps> = ({ title, value, icon, accent, description }) => {
  const accentStyles = {
    cyan: 'from-sky-400/20 to-sky-500/5 text-sky-200 border-sky-400/20',
    orange: 'from-pink-400/20 to-pink-500/5 text-pink-200 border-pink-400/20',
    emerald: 'from-emerald-400/20 to-emerald-500/5 text-emerald-200 border-emerald-400/20',
    rose: 'from-fuchsia-400/20 to-fuchsia-500/5 text-fuchsia-200 border-fuchsia-400/20',
    violet: 'from-violet-400/20 to-violet-500/5 text-violet-200 border-violet-400/20',
    amber: 'from-amber-400/20 to-orange-500/5 text-amber-200 border-amber-400/20',
  }

  return (
    <div className={`rounded-3xl border bg-gradient-to-br p-5 shadow-xl backdrop-blur ${accentStyles[accent]}`}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.16em] text-slate-400">{title}</p>
          <div className="mt-2 text-3xl font-black text-white">{value}</div>
          <div className="mt-2 text-sm text-slate-300">{description}</div>
        </div>
        <div className="rounded-2xl border border-white/10 bg-white/5 p-3 text-white shadow-lg">{icon}</div>
      </div>
    </div>
  )
}

const PanelCard: React.FC<{ title: string; subtitle: string; icon: React.ReactNode; children: React.ReactNode }> = ({
  title,
  subtitle,
  icon,
  children,
}) => {
  return (
    <div className="rounded-[1.75rem] border border-white/10 bg-white/5 p-5 shadow-xl backdrop-blur">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2 text-white">
            <h2 className="text-lg font-bold">{title}</h2>
            <span className="rounded-full border border-white/10 bg-white/5 p-1 text-slate-300">{icon}</span>
          </div>
          <p className="mt-1 text-sm text-slate-400">{subtitle}</p>
        </div>
      </div>
      {children}
    </div>
  )
}

const SuggestionCard: React.FC<{ suggestion: { title: string; severity: 'low' | 'medium' | 'high'; endpoint?: string | null; reason: string; action: string } }> = ({ suggestion }) => {
  const severityStyles = {
    low: 'border-slate-400/20 bg-slate-400/10 text-slate-200',
    medium: 'border-sky-400/20 bg-sky-400/10 text-sky-100',
    high: 'border-pink-400/20 bg-pink-400/10 text-pink-100',
  }

  return (
    <div className={`rounded-2xl border p-4 ${severityStyles[suggestion.severity]}`}>
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-semibold text-white">{suggestion.title}</div>
          <div className="mt-1 text-sm text-slate-200/80">{suggestion.reason}</div>
        </div>
        <span className="rounded-full bg-white/10 px-2.5 py-1 text-xs font-semibold uppercase tracking-wide text-white/90">
          {suggestion.severity}
        </span>
      </div>
      {suggestion.endpoint ? <div className="mt-3 text-sm text-slate-300">Endpoint: {suggestion.endpoint}</div> : null}
      <div className="mt-2 text-sm text-slate-100/90">{suggestion.action}</div>
    </div>
  )
}

const MetricStrip: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
    <div className="text-sm text-slate-400">{label}</div>
    <div className="mt-1 text-2xl font-black text-white">{value}</div>
  </div>
)

const InfoRow: React.FC<{ label: string; value: string }> = ({ label, value }) => (
  <div className="flex items-center justify-between gap-4 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
    <span className="text-slate-400">{label}</span>
    <span className="max-w-[60%] truncate font-medium text-white">{value}</span>
  </div>
)
