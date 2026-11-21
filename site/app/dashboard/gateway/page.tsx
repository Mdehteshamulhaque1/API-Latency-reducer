"use client"

import * as React from "react"
import Link from "next/link"
import {
  ArrowRight,
  Database,
  ExternalLink,
  FlaskConical,
  Gauge,
  Lightbulb,
  MessageSquare,
  RefreshCw,
  Route,
  ShieldAlert,
  TriangleAlert,
  Zap,
} from "lucide-react"

import { LatencyChart } from "@/components/charts/latency-chart"
import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { Pill, StatusCodePill, type PillTone } from "@/components/ui/pill"
import { RANGE_OPTIONS, Segmented, rangeLabel } from "@/components/ui/segmented"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table"
import {
  API_BASE_URL,
  apiAnalyticsBenchmark,
  apiAnalyticsEndpoints,
  apiRunBenchmark,
  apiSuggestions,
  type ApiLog,
  type BenchmarkReport,
  type LatencyPoint,
  type OptimizationSuggestion,
  type SuggestionSeverity,
} from "@/lib/api"
import { usePolling } from "@/lib/use-auth"
import { useMonitoredService } from "@/lib/use-service"
import { cn, formatDateTime, formatMs, formatPercent, formatRelative, num, parseUtc } from "@/lib/utils"

const CHAT_PATTERN = "/chat"
const LOG_LIMIT = 200

const SEVERITY_TONE: Record<SuggestionSeverity, PillTone> = {
  high: "red",
  medium: "amber",
  low: "zinc",
}

const PIPELINE = [
  { icon: Database, title: "Exact-match cache", body: "Identical prompts at temperature 0 are served from Redis." },
  { icon: Route, title: "Primary model", body: "Cache misses go to the configured primary model with retries." },
  { icon: ShieldAlert, title: "Circuit breaker", body: "Repeated failures open the breaker and skip a failing model." },
  { icon: Zap, title: "Fallback model", body: "Eligible failures are retried on the fallback model." },
]

interface GatewayStats {
  requests: number
  hits: number
  errors: number
  avgLatency: number
  avgHitLatency: number
  avgMissLatency: number
}

function summarise(logs: ApiLog[]): GatewayStats {
  const hits = logs.filter((log) => log.cache_hit)
  const misses = logs.filter((log) => !log.cache_hit)
  const average = (items: ApiLog[]) =>
    items.length ? items.reduce((sum, log) => sum + log.response_time_ms, 0) / items.length : 0
  return {
    requests: logs.length,
    hits: hits.length,
    errors: logs.filter((log) => log.status_code >= 400).length,
    avgLatency: average(logs),
    avgHitLatency: average(hits),
    avgMissLatency: average(misses),
  }
}

/** Bucket chat logs into per-15-minute averages for the latency chart. */
function toSeries(logs: ApiLog[]): LatencyPoint[] {
  const bucketMs = 15 * 60 * 1000
  const buckets = new Map<number, { total: number; count: number; errors: number }>()
  for (const log of logs) {
    const time = parseUtc(log.created_at).getTime()
    if (Number.isNaN(time)) continue
    const key = Math.floor(time / bucketMs) * bucketMs
    const bucket = buckets.get(key) ?? { total: 0, count: 0, errors: 0 }
    bucket.total += log.response_time_ms
    bucket.count += 1
    if (log.status_code >= 400) bucket.errors += 1
    buckets.set(key, bucket)
  }
  return Array.from(buckets.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([key, bucket]) => ({
      timestamp: new Date(key).toISOString(),
      avg_response_time_ms: bucket.total / bucket.count,
      request_count: bucket.count,
      error_count: bucket.errors,
    }))
}

function BenchmarkCard({ hours, service }: { hours: number; service?: string }) {
  const loader = React.useCallback(() => apiAnalyticsBenchmark(hours, { service }), [hours, service])
  const { data, loading, error, reload } = usePolling<BenchmarkReport>(loader, null)
  const [running, setRunning] = React.useState(false)
  const [runMessage, setRunMessage] = React.useState<string | null>(null)
  const [runError, setRunError] = React.useState<string | null>(null)

  async function run() {
    setRunning(true)
    setRunMessage(null)
    setRunError(null)
    try {
      const result = await apiRunBenchmark(hours)
      setRunMessage(`Report ${result.status} for the last ${rangeLabel(result.hours)}; persisting in the background.`)
      await reload()
    } catch (err) {
      setRunError(err instanceof Error ? err.message : "Benchmark run failed")
    } finally {
      setRunning(false)
    }
  }

  const improvement = num(data?.improvement_percent)
  const improved = improvement > 0

  return (
    <Panel
      title="Before / after benchmark"
      description="Splits the window in half and compares average latency"
      icon={<FlaskConical className="h-4 w-4" />}
      actions={
        <Button variant="subtle" size="sm" onClick={run} disabled={running || loading} className="gap-2">
          <RefreshCw className={cn("h-3.5 w-3.5", running && "animate-spin")} />
          {running ? "Running…" : "Run benchmark job"}
        </Button>
      }
    >
      {error && (
        <Alert variant="destructive" className="mb-4">
          {error}
        </Alert>
      )}
      {runError && (
        <Alert variant="destructive" className="mb-4">
          {runError}
        </Alert>
      )}
      {runMessage && (
        <Alert variant="success" className="mb-4">
          {runMessage}
        </Alert>
      )}
      {loading && !data ? (
        <Skeleton className="h-28 w-full" />
      ) : !data || data.sample_size === 0 ? (
        <EmptyState
          title="Not enough samples"
          body="The benchmark needs request logs on both halves of the window. Send some traffic and run it again."
        />
      ) : (
        <div className="grid gap-4 sm:grid-cols-[1fr_auto_1fr]">
          <div className="rounded border border-rule bg-frost p-4">
            <p className="mono-label">baseline</p>
            <p className="mt-2 font-mono text-3xl tracking-tight text-ink">
              {formatMs(data.baseline_avg_response_time_ms)}
            </p>
            <p className="mt-1 text-[11px] text-faint" title={data.before_window}>
              first half of the window
            </p>
          </div>
          <div className="flex flex-col items-center justify-center gap-1 px-2">
            <span
              className={cn(
                "font-mono text-xl",
                improved ? "text-relay" : improvement < 0 ? "text-signal" : "text-graphite",
              )}
            >
              {improved ? "−" : improvement < 0 ? "+" : ""}
              {formatPercent(Math.abs(improvement))}
            </span>
            <ArrowRight className="h-4 w-4 text-faint" />
            <span className="text-[11px] text-faint">{data.sample_size.toLocaleString()} samples</span>
          </div>
          <div className="rounded border border-rule bg-frost p-4">
            <p className="mono-label">optimized</p>
            <p className="mt-2 font-mono text-3xl tracking-tight text-ink">
              {formatMs(data.optimized_avg_response_time_ms)}
            </p>
            <p className="mt-1 text-[11px] text-faint" title={data.after_window}>
              second half of the window
            </p>
          </div>
        </div>
      )}
    </Panel>
  )
}

function SuggestionsCard({ hours, service }: { hours: number; service?: string }) {
  const loader = React.useCallback(() => apiSuggestions(hours, { service }), [hours, service])
  const { data, loading, error } = usePolling<OptimizationSuggestion[]>(loader, 60_000)
  const suggestions = data ?? []

  return (
    <Panel
      title="Optimization suggestions"
      description="Heuristics derived from request patterns"
      icon={<Lightbulb className="h-4 w-4" />}
      flush
    >
      {error && (
        <Alert variant="destructive" className="m-5">
          {error}
        </Alert>
      )}
      {loading && !data ? (
        <div className="space-y-3 p-5">
          {Array.from({ length: 3 }).map((_, index) => (
            <Skeleton key={index} className="h-16 w-full" />
          ))}
        </div>
      ) : suggestions.length === 0 ? (
        <EmptyState
          compact
          icon={<Lightbulb className="h-5 w-5" />}
          title="Nothing to flag"
          body="No endpoint in this window crosses the latency, error, or cache-miss thresholds."
        />
      ) : (
        <ul className="divide-y divide-rule">
          {suggestions.map((suggestion, index) => (
            <li key={`${suggestion.title}-${index}`} className="px-5 py-4">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-sm text-ink">{suggestion.title}</p>
                  {suggestion.endpoint && (
                    <p className="mt-0.5 truncate font-mono text-[12px] text-graphite">{suggestion.endpoint}</p>
                  )}
                </div>
                <Pill tone={SEVERITY_TONE[suggestion.severity] ?? "zinc"}>{suggestion.severity}</Pill>
              </div>
              <p className="mt-2 text-xs leading-relaxed text-graphite">{suggestion.reason}</p>
              <p className="mt-1.5 flex items-start gap-1.5 text-xs leading-relaxed text-ink">
                <ArrowRight className="mt-0.5 h-3 w-3 shrink-0 text-steel" />
                {suggestion.action}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  )
}

export default function GatewayPage() {
  const [hours, setHours] = React.useState(24)
  const monitored = useMonitoredService()
  const service = monitored.service ?? undefined
  const monitoring = monitored.monitoring
  const label = monitored.label
  // For a monitored service, its own inbound POST /api/v1/chat requests are
  // listed (Esone proxies them to this gateway's answers pipeline). The method
  // filter keeps GET /api/v1/chat/history and /chat/status out of the count.
  const loader = React.useCallback(
    () =>
      apiAnalyticsEndpoints({
        pattern: CHAT_PATTERN,
        method: "POST",
        hours,
        limit: LOG_LIMIT,
        service,
        direction: service ? "inbound" : undefined,
      }),
    [hours, service],
  )
  const { data: logs, loading, error, reload, updatedAt } = usePolling<ApiLog[]>(
    loader,
    monitored.loading ? null : 30_000,
  )

  const chatLogs = React.useMemo(() => logs ?? [], [logs])
  const stats = React.useMemo(() => summarise(chatLogs), [chatLogs])
  const series = React.useMemo(() => toSeries(chatLogs), [chatLogs])
  const initial = loading && !logs
  const hitRate = stats.requests ? (stats.hits / stats.requests) * 100 : 0

  return (
    <>
      <PageHeader
        eyebrow={monitoring ? "chat traffic" : "llm gateway"}
        title={monitoring ? `${label} chat traffic` : "LLM gateway"}
        description={
          monitoring
            ? `Questions ${label}'s users asked through its POST /api/v1/chat, how many were answered from the semantic cache, their latency, and a before/after benchmark.`
            : "Traffic on POST /api/v1/chat, cache behaviour, routing, and benchmarks."
        }
        actions={
          <>
            <Segmented value={hours} onChange={setHours} options={RANGE_OPTIONS} ariaLabel="Time range" />
            <Button variant="outline" size="sm" onClick={reload} disabled={loading} className="gap-2">
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
              Refresh
            </Button>
          </>
        }
      />

      {error && (
        <Alert variant="destructive" className="mb-6">
          {error}
        </Alert>
      )}

      <div className="housing housing-row grid sm:grid-cols-2 lg:grid-cols-4">
        {initial ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-[120px]" />)
        ) : (
          <>
            <StatCard
              label="Chat requests"
              value={stats.requests.toLocaleString()}
              hint={`newest ${LOG_LIMIT} in the last ${rangeLabel(hours)}`}
              tone="indigo"
              icon={<MessageSquare className="h-4 w-4" />}
            />
            <StatCard
              label="Cache hit rate"
              value={formatPercent(hitRate)}
              hint={monitoring ? `${stats.hits} answered from the semantic cache` : `${stats.hits} served from Redis`}
              tone="emerald"
              icon={<Database className="h-4 w-4" />}
            />
            <StatCard
              label="Avg latency"
              value={formatMs(stats.avgLatency)}
              hint={
                stats.hits && stats.requests - stats.hits
                  ? `hit ${formatMs(stats.avgHitLatency, 0)}, miss ${formatMs(stats.avgMissLatency, 0)}`
                  : "gateway round trip"
              }
              tone="cyan"
              icon={<Gauge className="h-4 w-4" />}
            />
            <StatCard
              label="Errors"
              value={stats.errors.toLocaleString()}
              hint={stats.requests ? formatPercent((stats.errors / stats.requests) * 100) : "no traffic"}
              tone={stats.errors > 0 ? "amber" : "emerald"}
              icon={<TriangleAlert className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      {!monitoring && (
      <Card className="mt-4 p-5">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-medium text-ink">Request path</h2>
          <span className="font-mono text-[11px] text-steel">POST /api/v1/chat</span>
        </div>
        <ol className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {PIPELINE.map((step, index) => (
            <li key={step.title} className="relative rounded border border-rule bg-frost p-4">
              <div className="flex items-center gap-2">
                <span className="flex h-7 w-7 items-center justify-center rounded border border-rule bg-frost">
                  <step.icon className="h-3.5 w-3.5 text-steel" />
                </span>
                <span className="font-mono text-[10px] text-faint">0{index + 1}</span>
              </div>
              <p className="mt-3 text-sm text-ink">{step.title}</p>
              <p className="mt-1 text-xs leading-relaxed text-graphite">{step.body}</p>
            </li>
          ))}
        </ol>
      </Card>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel
          title="Chat latency"
          description="Average per 15-minute bucket, from the logged requests"
          actions={updatedAt ? <span className="mono-label">updated {formatRelative(updatedAt)}</span> : undefined}
        >
          {initial ? <Skeleton className="h-[240px] w-full" /> : <LatencyChart data={series} />}
        </Panel>
        <BenchmarkCard hours={hours} service={service} />
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel
          title={monitoring ? `Recent ${label} questions` : "Recent gateway calls"}
          description="Newest chat requests with cache outcome"
          icon={<MessageSquare className="h-4 w-4" />}
          flush
        >
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : chatLogs.length === 0 ? (
            <EmptyState
              compact
              icon={<MessageSquare className="h-5 w-5" />}
              title="No chat traffic yet"
              body="Requests through POST /api/v1/chat will appear here."
            />
          ) : (
            <Table minWidth={620}>
              <THead>
                <tr>
                  <TH>Time</TH>
                  <TH>Status</TH>
                  <TH>Cache</TH>
                  <TH align="right">Latency</TH>
                  <TH>Correlation ID</TH>
                </tr>
              </THead>
              <TBody>
                {chatLogs.slice(0, 12).map((log) => (
                  <TR key={log.id}>
                    <TD className="whitespace-nowrap text-xs text-faint">{formatDateTime(log.created_at)}</TD>
                    <TD>
                      <StatusCodePill status={log.status_code} />
                    </TD>
                    <TD>
                      <Pill tone={log.cache_hit ? "emerald" : "zinc"}>{log.cache_hit ? "hit" : "miss"}</Pill>
                    </TD>
                    <TD mono align="right">
                      {formatMs(log.response_time_ms)}
                    </TD>
                    <TD mono className="max-w-[180px] truncate text-faint" title={log.correlation_id}>
                      {log.correlation_id}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </Panel>

        <div className="space-y-4">
          <SuggestionsCard hours={hours} />
          <Card className="p-5">
            <h2 className="text-sm font-medium text-ink">Prometheus metrics</h2>
            <p className="mt-1 text-xs leading-relaxed text-graphite">
              Per-model request counts, latency histograms, cache hits, and circuit breaker state are exported at
              GET /metrics.
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3 gap-2"
              onClick={() => window.open(`${API_BASE_URL}/metrics`, "_blank", "noopener")}
            >
              Open /metrics
              <ExternalLink className="h-3.5 w-3.5" />
            </Button>
          </Card>
        </div>
      </div>
    </>
  )
}
