import { motion } from 'framer-motion'
import { Link } from 'react-router-dom'
import {
  Activity,
  Timer,
  PieChart,
  AlertTriangle,
  ArrowRight,
  Lightbulb,
  Database,
  TrendingDown,
  ArrowUpRight,
} from 'lucide-react'
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  BarChart,
  Bar,
  Cell,
} from 'recharts'
import { useDashboardData } from '../context/DashboardDataContext'
import { StatCard, Card, PageHeader, Badge, Skeleton, LoadingBlock } from '../components/dashboard/ui'
import { formatMs, formatNumber, formatPercent, formatTimestamp, severityTone } from '../lib/format'
import AnimatedCounter from '../components/AnimatedCounter'

const BAR_COLORS = ['#4f46e5', '#7c3aed', '#06b6d4', '#22d3ee', '#8b5cf6', '#0ea5e9']

export default function Overview() {
  const { loading, summary } = useDashboardData()

  if (loading) {
    return (
      <div className="space-y-6">
        <PageHeader title="Overview" />
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
          {[0, 1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
        <div className="grid gap-6 lg:grid-cols-3">
          <Skeleton className="h-80 lg:col-span-2" />
          <Skeleton className="h-80" />
        </div>
        <LoadingBlock label="Loading analytics…" />
      </div>
    )
  }

  const series =
    summary?.latency_series?.map((p) => ({
      ...p,
      label: formatTimestamp(p.timestamp, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' }),
    })) || []

  const endpointData = summary?.top_endpoints?.slice(0, 8) || []

  return (
    <div>
      <PageHeader
        title="Overview"
        description="A live snapshot of your API performance across the last 24 hours."
        actions={
          <Link
            to="/dashboard/analytics"
            className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-600 transition-colors hover:border-brand-400 hover:text-brand-600"
          >
            Deep analytics <ArrowRight size={15} />
          </Link>
        }
      />

      {/* Stat cards */}
      <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Total requests"
          value={<AnimatedCounter value={summary?.total_requests || 0} />}
          sub={`≈ ${summary?.request_rate_per_minute ?? 0} req/min`}
          icon={Activity}
          gradient="from-brand-500 to-violet-500"
          delay={0}
        />
        <StatCard
          label="Avg latency"
          value={<AnimatedCounter value={summary?.avg_response_time_ms || 0} suffix="ms" />}
          sub={
            <span className="inline-flex items-center gap-1 text-emerald-600">
              <TrendingDown size={13} /> benchmark improved
            </span>
          }
          icon={Timer}
          gradient="from-accent-500 to-cyan-500"
          delay={0.06}
        />
        <StatCard
          label="Cache hit rate"
          value={<AnimatedCounter value={summary?.cache_hit_rate || 0} decimals={1} suffix="%" />}
          sub={`${formatPercent(summary?.cache_miss_rate)} miss rate`}
          icon={PieChart}
          gradient="from-emerald-500 to-teal-500"
          delay={0.12}
        />
        <StatCard
          label="Error rate"
          value={<AnimatedCounter value={summary?.error_rate || 0} decimals={2} suffix="%" />}
          sub={`${formatNumber(summary?.total_errors)} total errors`}
          icon={AlertTriangle}
          gradient="from-rose-500 to-orange-500"
          delay={0.18}
        />
      </div>

      {/* Latency + endpoints */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="lg:col-span-2"
        >
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg font-bold text-slate-900">Latency over time</h3>
                <p className="text-xs text-slate-400">Average response time per bucket</p>
              </div>
              <Badge tone="brand">
                <Timer size={12} /> ms
              </Badge>
            </div>
            <div className="mt-5 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={series} margin={{ top: 6, right: 4, left: -14, bottom: 0 }}>
                  <defs>
                    <linearGradient id="latGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#4f46e5" stopOpacity={0.3} />
                      <stop offset="100%" stopColor="#4f46e5" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
                  <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} minTickGap={28} />
                  <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                    labelStyle={{ fontWeight: 600 }}
                    formatter={(value) => [`${Math.round(value)} ms`, 'Avg latency']}
                  />
                  <Area type="monotone" dataKey="avg_response_time_ms" stroke="#4f46e5" strokeWidth={2.5} fill="url(#latGrad)" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.18 }}
        >
          <Card className="h-full">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg font-bold text-slate-900">Top endpoints</h3>
                <p className="text-xs text-slate-400">By request count</p>
              </div>
              <Badge tone="slate">{endpointData.length} routes</Badge>
            </div>
            <div className="mt-5 h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={endpointData} layout="vertical" margin={{ top: 0, right: 12, left: 8, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" horizontal={false} />
                  <XAxis type="number" tick={{ fontSize: 10, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                  <YAxis
                    type="category"
                    dataKey="endpoint"
                    width={148}
                    tick={{ fontSize: 9.5, fill: '#64748b' }}
                    axisLine={false}
                    tickLine={false}
                    tickFormatter={(v) => v.replace('/api/v1', '').slice(0, 22) || v}
                  />
                  <Tooltip
                    contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                    formatter={(value) => [formatNumber(value), 'Requests']}
                  />
                  <Bar dataKey="count" radius={[0, 6, 6, 0]} barSize={14}>
                    {endpointData.map((_, i) => (
                      <Cell key={i} fill={BAR_COLORS[i % BAR_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
        </motion.div>
      </div>

      {/* Recent requests + suggestions + benchmark */}
      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.24 }}
          className="lg:col-span-2"
        >
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg font-bold text-slate-900">Recent requests</h3>
                <p className="text-xs text-slate-400">Latest activity across your API</p>
              </div>
              <Badge tone="green">
                <Activity size={12} /> live feed
              </Badge>
            </div>
            <div className="mt-5 overflow-x-auto scrollbar-thin">
              <table className="w-full min-w-[560px] text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-100 text-[11px] uppercase tracking-widest text-slate-400">
                    <th className="pb-3 pr-4 font-semibold">Endpoint</th>
                    <th className="pb-3 pr-4 font-semibold">Method</th>
                    <th className="pb-3 pr-4 font-semibold">Status</th>
                    <th className="pb-3 pr-4 font-semibold">Latency</th>
                    <th className="pb-3 font-semibold">Cache</th>
                  </tr>
                </thead>
                <tbody>
                  {(summary?.recent_requests || []).map((r, i) => (
                    <tr key={i} className="border-b border-slate-50 transition-colors last:border-0 hover:bg-slate-50/70">
                      <td className="py-3 pr-4">
                        <p className="max-w-[220px] truncate font-medium text-slate-700">{r.endpoint}</p>
                        <p className="text-[11px] text-slate-400">{formatTimestamp(r.created_at)}</p>
                      </td>
                      <td className="py-3 pr-4">
                        <span
                          className={`rounded-md px-2 py-1 text-[11px] font-bold ${
                            r.method === 'GET' ? 'bg-brand-50 text-brand-600' : 'bg-violet-50 text-violet-600'
                          }`}
                        >
                          {r.method}
                        </span>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge tone={r.status_code >= 400 ? 'red' : 'green'}>{r.status_code}</Badge>
                      </td>
                      <td className="py-3 pr-4 font-medium text-slate-600">{formatMs(r.response_time_ms)}</td>
                      <td className="py-3">
                        {r.cache_hit ? <Badge tone="brand">hit</Badge> : <Badge tone="slate">miss</Badge>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </motion.div>

        <div className="space-y-6">
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.3 }}>
            <Card>
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-bold text-slate-900">Suggestions</h3>
                <Lightbulb size={18} className="text-amber-400" />
              </div>
              <div className="mt-4 space-y-3">
                {(summary?.optimization_suggestions || []).slice(0, 3).map((s, i) => (
                  <div key={i} className="rounded-xl border border-slate-100 bg-slate-50/60 p-4 transition-colors hover:border-brand-200 hover:bg-brand-50/40">
                    <div className="flex items-center gap-2">
                      <Badge tone={severityTone(s.severity)}>{s.severity}</Badge>
                      <p className="text-sm font-bold text-slate-800">{s.title}</p>
                    </div>
                    <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{s.reason}</p>
                  </div>
                ))}
                {!summary?.optimization_suggestions?.length && (
                  <p className="text-sm text-slate-400">No suggestions yet.</p>
                )}
              </div>
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.36 }}>
            <Card className="relative overflow-hidden">
              <div
                className="pointer-events-none absolute -right-10 -top-10 h-32 w-32 rounded-full bg-gradient-to-br from-emerald-500 to-teal-500 opacity-10 blur-2xl"
              />
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-bold text-slate-900">Benchmark</h3>
                <Database size={18} className="text-brand-500" />
              </div>
              <p className="mt-1 text-xs text-slate-400">Before / after optimization</p>

              <div className="mt-5 flex items-end gap-6">
                <div className="flex-1">
                  <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">Baseline</p>
                  <p className="font-display mt-1 text-2xl font-bold text-slate-700">
                    {formatMs(summary?.benchmark?.baseline_avg_response_time_ms)}
                  </p>
                </div>
                <ArrowUpRight size={20} className="mb-1 text-slate-300" />
                <div className="flex-1">
                  <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">Optimized</p>
                  <p className="font-display mt-1 text-2xl font-bold text-emerald-600">
                    {formatMs(summary?.benchmark?.optimized_avg_response_time_ms)}
                  </p>
                </div>
              </div>

              <div className="mt-5">
                <div className="flex justify-between text-xs text-slate-400">
                  <span>Baseline</span>
                  <span className="font-bold text-emerald-600">
                    −{summary?.benchmark?.improvement_percent ?? 0}%
                  </span>
                  <span>Optimized</span>
                </div>
                <div className="relative mt-2 h-2.5 overflow-hidden rounded-full bg-slate-100">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{
                      width: `${Math.min(100, (summary?.benchmark?.improvement_percent ?? 0) * 2.4)}%`,
                    }}
                    transition={{ duration: 1.2, ease: 'easeOut', delay: 0.4 }}
                    className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400"
                  />
                </div>
              </div>
              <p className="mt-4 text-[11px] text-slate-400">
                Sample size: {formatNumber(summary?.benchmark?.sample_size)} requests
              </p>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
