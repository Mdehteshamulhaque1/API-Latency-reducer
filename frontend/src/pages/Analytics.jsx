import { useState } from 'react'
import { motion } from 'framer-motion'
import { Timer, Flame, Lightbulb, GaugeCircle, RefreshCw } from 'lucide-react'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  Legend,
} from 'recharts'
import { useDashboardQuery } from '../hooks/useDashboardQuery'
import { apiClient } from '../lib/apiClient'
import { Card, PageHeader, Badge, LoadingBlock } from '../components/dashboard/ui'
import { formatMs, formatNumber, formatPercent, formatTimestamp, severityTone } from '../lib/format'

const periods = [
  { value: 12, label: '12h' },
  { value: 24, label: '24h' },
  { value: 48, label: '48h' },
  { value: 168, label: '7d' },
]

export default function Analytics() {
  const [hours, setHours] = useState(24)

  const periodSummary = useDashboardQuery(() => apiClient.summary(hours), [hours])
  const slow = useDashboardQuery(() => apiClient.slowEndpoints(hours, 10), [hours])
  const benchmark = useDashboardQuery(() => apiClient.benchmark(hours), [hours])
  const suggestions = useDashboardQuery(() => apiClient.suggestions(hours), [hours])

  const distribution =
    periodSummary.data?.latency_distribution?.map((p) => ({
      ...p,
      label: formatTimestamp(p.timestamp, { month: 'short', day: 'numeric', hour: '2-digit' }),
    })) || []

  const benchmarkData = benchmark.data
  const improvement = benchmarkData?.improvement_percent ?? 0

  return (
    <div>
      <PageHeader
        title="Analytics"
        description="Deep performance analytics with percentile latencies and endpoint rankings."
        actions={
          <div className="inline-flex items-center gap-1 rounded-xl border border-slate-200 bg-white p-1">
            {periods.map((p) => (
              <button
                key={p.value}
                onClick={() => setHours(p.value)}
                className={`rounded-lg px-3.5 py-2 text-xs font-bold transition-all ${
                  hours === p.value
                    ? 'bg-gradient-to-r from-brand-600 to-violet-600 text-white shadow'
                    : 'text-slate-500 hover:text-brand-600'
                }`}
              >
                {p.label}
              </button>
            ))}
          </div>
        }
      />

      {/* Latency distribution */}
      <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }}>
        <Card>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-display text-lg font-bold text-slate-900">Latency distribution</h3>
              <p className="text-xs text-slate-400">Avg vs P95 vs P99 across time buckets</p>
            </div>
            <Badge tone="brand">
              <Timer size={12} /> percentiles
            </Badge>
          </div>
          <div className="mt-5 h-80">
            {periodSummary.loading && !distribution.length ? (
              <LoadingBlock label="Loading latency data…" />
            ) : (
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={distribution} margin={{ top: 6, right: 8, left: -12, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef2f7" vertical={false} />
                <XAxis dataKey="label" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} minTickGap={24} />
                <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: '1px solid #e2e8f0', fontSize: 12 }}
                  labelStyle={{ fontWeight: 600 }}
                  formatter={(value, name) => [`${Math.round(value)} ms`, name]}
                />
                <Legend wrapperStyle={{ fontSize: 12 }} />
                <Line type="monotone" dataKey="avg_response_time_ms" name="Avg" stroke="#06b6d4" strokeWidth={2.2} dot={false} />
                <Line type="monotone" dataKey="p95_response_time_ms" name="P95" stroke="#6366f1" strokeWidth={2.4} dot={false} />
                <Line type="monotone" dataKey="p99_response_time_ms" name="P99" stroke="#f43f5e" strokeWidth={2.2} dot={false} strokeDasharray="5 4" />
              </LineChart>
            </ResponsiveContainer>
            )}
          </div>
        </Card>
      </motion.div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Slow endpoints */}
        <motion.div
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="lg:col-span-2"
        >
          <Card>
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-display text-lg font-bold text-slate-900">Slow endpoint ranking</h3>
                <p className="text-xs text-slate-400">Ranked by P95 latency — the biggest wins live here</p>
              </div>
              <Badge tone="red">
                <Flame size={12} /> hottest first
              </Badge>
            </div>

            {slow.loading ? (
              <LoadingBlock label="Ranking endpoints…" />
            ) : (
              <div className="mt-5 overflow-x-auto scrollbar-thin">
                <table className="w-full min-w-[620px] text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-100 text-[11px] uppercase tracking-widest text-slate-400">
                      <th className="pb-3 pr-4 font-semibold">#</th>
                      <th className="pb-3 pr-4 font-semibold">Endpoint</th>
                      <th className="pb-3 pr-4 font-semibold">Requests</th>
                      <th className="pb-3 pr-4 font-semibold">Avg</th>
                      <th className="pb-3 pr-4 font-semibold">P95</th>
                      <th className="pb-3 pr-4 font-semibold">P99</th>
                      <th className="pb-3 pr-4 font-semibold">Errors</th>
                      <th className="pb-3 font-semibold">Cache rate</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(slow.data || []).map((e, i) => (
                      <tr key={i} className="border-b border-slate-50 transition-colors last:border-0 hover:bg-slate-50/70">
                        <td className="py-3.5 pr-4">
                          <span
                            className={`flex h-6 w-6 items-center justify-center rounded-md text-[11px] font-bold ${
                              i < 3 ? 'bg-gradient-to-br from-rose-500 to-orange-500 text-white' : 'bg-slate-100 text-slate-500'
                            }`}
                          >
                            {i + 1}
                          </span>
                        </td>
                        <td className="py-3.5 pr-4">
                          <p className="max-w-[200px] truncate font-medium text-slate-700">{e.endpoint}</p>
                        </td>
                        <td className="py-3.5 pr-4 text-slate-600">{formatNumber(e.count)}</td>
                        <td className="py-3.5 pr-4 text-slate-600">{formatMs(e.avg_time)}</td>
                        <td className="py-3.5 pr-4 font-semibold text-slate-800">{formatMs(e.p95_time)}</td>
                        <td className="py-3.5 pr-4 font-semibold text-rose-600">{formatMs(e.p99_time)}</td>
                        <td className="py-3.5 pr-4">
                          <Badge tone={e.errors > 0 ? 'red' : 'green'}>{e.errors}</Badge>
                        </td>
                        <td className="py-3.5">
                          <div className="flex items-center gap-2">
                            <div className="h-1.5 w-16 overflow-hidden rounded-full bg-slate-100">
                              <div
                                className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-500"
                                style={{ width: `${Math.min(100, e.cache_hit_rate)}%` }}
                              />
                            </div>
                            <span className="text-xs text-slate-500">{formatPercent(e.cache_hit_rate, 0)}</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>
        </motion.div>

        {/* Benchmark + suggestions column */}
        <div className="space-y-6">
          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}>
            <Card>
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-bold text-slate-900">Benchmark</h3>
                <GaugeCircle size={18} className="text-brand-500" />
              </div>

              {benchmark.loading ? (
                <LoadingBlock label="Computing benchmark…" />
              ) : (
                <>
                  <div className="mt-5 flex items-center justify-center">
                    <div className="relative flex h-32 w-32 items-center justify-center rounded-full">
                      <svg viewBox="0 0 120 120" className="h-32 w-32 -rotate-90">
                        <circle cx="60" cy="60" r="52" fill="none" stroke="#eef2f7" strokeWidth="10" />
                        <motion.circle
                          cx="60"
                          cy="60"
                          r="52"
                          fill="none"
                          stroke="#10b981"
                          strokeWidth="10"
                          strokeLinecap="round"
                          strokeDasharray={2 * Math.PI * 52}
                          initial={{ strokeDashoffset: 2 * Math.PI * 52 }}
                          animate={{ strokeDashoffset: 2 * Math.PI * 52 * (1 - Math.min(improvement, 100) / 100) }}
                          transition={{ duration: 1.4, ease: 'easeOut' }}
                        />
                      </svg>
                      <div className="absolute text-center">
                        <p className="font-display text-2xl font-bold text-emerald-600">{improvement}%</p>
                        <p className="text-[10px] uppercase tracking-widest text-slate-400">improvement</p>
                      </div>
                    </div>
                  </div>
                  <div className="mt-5 grid grid-cols-2 gap-3 text-center">
                    <div className="rounded-xl bg-slate-50 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-widest text-slate-400">Baseline</p>
                      <p className="font-display mt-1 text-lg font-bold text-slate-700">
                        {formatMs(benchmarkData?.baseline_avg_response_time_ms)}
                      </p>
                    </div>
                    <div className="rounded-xl bg-emerald-50 p-3">
                      <p className="text-[11px] font-semibold uppercase tracking-widest text-emerald-500">Optimized</p>
                      <p className="font-display mt-1 text-lg font-bold text-emerald-700">
                        {formatMs(benchmarkData?.optimized_avg_response_time_ms)}
                      </p>
                    </div>
                  </div>
                  <p className="mt-4 text-[11px] text-slate-400">
                    {formatNumber(benchmarkData?.sample_size)} requests sampled across the selected window.
                  </p>
                </>
              )}
            </Card>
          </motion.div>

          <motion.div initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.26 }}>
            <Card>
              <div className="flex items-center justify-between">
                <h3 className="font-display text-lg font-bold text-slate-900">Suggestions</h3>
                <Lightbulb size={18} className="text-amber-400" />
              </div>
              <div className="mt-4 space-y-3">
                {(suggestions.data || []).map((s, i) => (
                  <div
                    key={i}
                    className="rounded-xl border border-slate-100 bg-slate-50/60 p-4 transition-colors hover:border-brand-200 hover:bg-brand-50/40"
                  >
                    <div className="flex items-center gap-2">
                      <Badge tone={severityTone(s.severity)}>{s.severity}</Badge>
                      <p className="text-sm font-bold text-slate-800">{s.title}</p>
                    </div>
                    <p className="mt-1.5 text-xs leading-relaxed text-slate-500">{s.reason}</p>
                    {s.action && (
                      <p className="mt-2 flex items-start gap-1.5 text-xs text-brand-600">
                        <RefreshCw size={12} className="mt-0.5 shrink-0" />
                        {s.action}
                      </p>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          </motion.div>
        </div>
      </div>
    </div>
  )
}
