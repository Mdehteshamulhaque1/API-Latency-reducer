"use client"

import * as React from "react"
import {
  Activity,
  Database,
  ListChecks,
  RefreshCw,
  Search,
  Timer,
  TriangleAlert,
  Turtle,
  Zap,
} from "lucide-react"

import { CacheChart } from "@/components/charts/cache-chart"
import { LatencyDistributionChart } from "@/components/charts/latency-distribution-chart"
import { TrafficChart } from "@/components/charts/traffic-chart"
import { DirectionPill } from "@/components/dashboard/service-switch"
import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { MethodPill, Pill, StatusCodePill } from "@/components/ui/pill"
import { RANGE_OPTIONS, Segmented, rangeLabel, type SegmentedOption } from "@/components/ui/segmented"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table"
import {
  apiAnalyticsEndpoints,
  apiAnalyticsSummary,
  type AnalyticsSummary,
  type ApiLog,
  type RequestDirection,
} from "@/lib/api"
import { usePolling } from "@/lib/use-auth"
import { useMonitoredService } from "@/lib/use-service"
import { cn, formatDateTime, formatMs, formatPercent, formatRelative, formatTime, num } from "@/lib/utils"

const LOG_LIMIT = 50

type DirectionChoice = RequestDirection | "all"

const DIRECTION_OPTIONS: ReadonlyArray<SegmentedOption<DirectionChoice>> = [
  { value: "all", label: "all" },
  { value: "inbound", label: "in" },
  { value: "outbound", label: "out" },
]

function RequestLogExplorer({ hours, service }: { hours: number; service: string | null }) {
  const [pattern, setPattern] = React.useState("")
  const [applied, setApplied] = React.useState("")
  const [direction, setDirection] = React.useState<DirectionChoice>("all")
  const [logs, setLogs] = React.useState<ApiLog[]>([])
  const [loading, setLoading] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const monitoring = service !== null

  const load = React.useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setLogs(
        await apiAnalyticsEndpoints({
          pattern: applied,
          hours,
          limit: LOG_LIMIT,
          service: service ?? undefined,
          direction: direction === "all" ? undefined : direction,
        }),
      )
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load request logs")
    } finally {
      setLoading(false)
    }
  }, [applied, hours, service, direction])

  React.useEffect(() => {
    void load()
  }, [load])

  function submit(event: React.FormEvent) {
    event.preventDefault()
    setApplied(pattern.trim())
  }

  return (
    <Panel
      title="Request log explorer"
      description={`Newest ${LOG_LIMIT} requests from GET /api/v1/analytics/endpoints, substring match on the endpoint`}
      icon={<Search className="h-4 w-4" />}
      actions={
        <form onSubmit={submit} className="flex items-center gap-2">
          {monitoring && (
            <Segmented value={direction} onChange={setDirection} options={DIRECTION_OPTIONS} ariaLabel="Direction" />
          )}
          <Input
            value={pattern}
            onChange={(event) => setPattern(event.target.value)}
            placeholder="/api/v1/chat"
            className="h-8 w-48 text-[13px]"
            aria-label="Endpoint pattern"
          />
          <Button type="submit" variant="subtle" size="sm" disabled={loading}>
            Search
          </Button>
        </form>
      }
      flush
    >
      {error && (
        <Alert variant="destructive" className="m-5">
          {error}
        </Alert>
      )}
      {loading && logs.length === 0 ? (
        <div className="space-y-3 p-5">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-10 w-full" />
          ))}
        </div>
      ) : logs.length === 0 ? (
        <EmptyState
          compact
          icon={<Search className="h-5 w-5" />}
          title="No matching requests"
          body={
            applied
              ? `Nothing containing "${applied}" in the last ${rangeLabel(hours)}.`
              : `No requests were logged in the last ${rangeLabel(hours)}.`
          }
        />
      ) : (
        <Table minWidth={900}>
          <THead>
            <tr>
              <TH>Time</TH>
              {monitoring && <TH>Dir</TH>}
              <TH>Request</TH>
              <TH>Status</TH>
              <TH align="right">Latency</TH>
              <TH>Cache</TH>
              <TH>Client</TH>
              <TH>Correlation ID</TH>
            </tr>
          </THead>
          <TBody>
            {logs.map((log) => (
              <TR key={log.id}>
                <TD className="whitespace-nowrap text-xs text-faint" title={log.created_at}>
                  {formatDateTime(log.created_at)}
                </TD>
                {monitoring && (
                  <TD>
                    <DirectionPill direction={log.direction} />
                  </TD>
                )}
                <TD>
                  <div className="flex items-center gap-2">
                    <MethodPill method={log.method} />
                    <span className="max-w-[260px] truncate font-mono text-[13px] text-ink">
                      {log.endpoint}
                    </span>
                  </div>
                  {log.error_message && (
                    <p className="mt-1 max-w-xs truncate text-[11px] text-signal">{log.error_message}</p>
                  )}
                </TD>
                <TD>
                  <StatusCodePill status={log.status_code} />
                </TD>
                <TD mono align="right">
                  {formatMs(log.response_time_ms)}
                </TD>
                <TD>
                  <Pill tone={log.cache_hit ? "emerald" : "zinc"}>{log.cache_hit ? "hit" : "miss"}</Pill>
                </TD>
                <TD mono className="text-graphite">
                  {log.client_ip}
                </TD>
                <TD mono className="max-w-[160px] truncate text-faint" title={log.correlation_id}>
                  {log.correlation_id}
                </TD>
              </TR>
            ))}
          </TBody>
        </Table>
      )}
    </Panel>
  )
}

export default function AnalyticsPage() {
  const [hours, setHours] = React.useState(24)
  const monitored = useMonitoredService()
  const service = monitored.service
  const loader = React.useCallback(
    () => apiAnalyticsSummary(hours, { service: service ?? undefined }),
    [hours, service],
  )
  const { data: summary, loading, error, reload, updatedAt } = usePolling<AnalyticsSummary>(
    loader,
    monitored.loading ? null : 30_000,
  )
  const monitoring = monitored.monitoring
  const scopeLabel = monitored.label

  const ranking = summary?.slow_endpoint_ranking ?? []
  const topEndpoints = summary?.top_endpoints ?? []
  const recent = summary?.recent_requests ?? []
  const hitRate = num(summary?.cache_hit_rate)
  const errorRate = num(summary?.error_rate)
  const initial = loading && !summary

  return (
    <>
      <PageHeader
        eyebrow="analytics"
        title={monitoring ? `${scopeLabel} traffic & latency` : "Traffic & latency"}
        description={
          monitoring
            ? `Every request ${scopeLabel} served (in) and every call it made to other services (out), shipped to this gateway's request log.`
            : "Request volume, latency percentiles, cache efficiency, and the slowest endpoints for the selected window."
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

      <div className="housing housing-row grid sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {initial ? (
          Array.from({ length: 6 }).map((_, index) => <Skeleton key={index} className="h-[120px]" />)
        ) : (
          <>
            <StatCard
              label="Requests"
              value={num(summary?.total_requests).toLocaleString()}
              hint={`${num(summary?.request_rate_per_minute).toFixed(2)} / min`}
              tone="indigo"
              icon={<Activity className="h-4 w-4" />}
            />
            <StatCard
              label="Avg latency"
              value={formatMs(num(summary?.avg_response_time_ms))}
              hint={`last ${rangeLabel(hours)}`}
              tone="cyan"
              icon={<Zap className="h-4 w-4" />}
            />
            <StatCard
              label="p50 / p95"
              value={`${formatMs(num(summary?.overall_p50_response_time_ms), 0)} / ${formatMs(num(summary?.overall_p95_response_time_ms), 0)}`}
              hint="median and 95th percentile"
              tone="indigo"
              icon={<Timer className="h-4 w-4" />}
            />
            <StatCard
              label="p99"
              value={formatMs(num(summary?.overall_p99_response_time_ms), 0)}
              hint="99th percentile"
              tone="indigo"
              icon={<Timer className="h-4 w-4" />}
            />
            <StatCard
              label="Cache hit rate"
              value={formatPercent(hitRate)}
              hint={`${formatPercent(num(summary?.cache_miss_rate))} miss`}
              tone="emerald"
              icon={<Database className="h-4 w-4" />}
            />
            <StatCard
              label="Error rate"
              value={formatPercent(errorRate)}
              hint={`${num(summary?.total_errors).toLocaleString()} errors, ${num(summary?.rate_limited_requests).toLocaleString()} rate limited`}
              tone={errorRate > 1 ? "amber" : "emerald"}
              icon={<TriangleAlert className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel
          title="Latency percentiles"
          description="Average, p95, and p99 per bucket"
          actions={updatedAt ? <span className="mono-label">updated {formatRelative(updatedAt)}</span> : undefined}
        >
          {initial ? (
            <Skeleton className="h-[260px] w-full" />
          ) : (
            <LatencyDistributionChart data={summary?.latency_distribution ?? []} />
          )}
        </Panel>
        <Panel title="Cache efficiency" description="Share of requests served from Redis">
          {initial ? (
            <Skeleton className="h-[240px] w-full" />
          ) : (
            <CacheChart totalRequests={num(summary?.total_requests)} hitRate={hitRate} />
          )}
        </Panel>
      </div>

      <Panel className="mt-4" title="Traffic" description="Requests per bucket, split into successful and errored">
        {initial ? <Skeleton className="h-[240px] w-full" /> : <TrafficChart data={summary?.latency_series ?? []} />}
      </Panel>

      <Panel
        className="mt-4"
        title="Slowest endpoints"
        description="Ranked by p95 latency"
        icon={<Turtle className="h-4 w-4" />}
        flush
      >
        {initial ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : ranking.length === 0 ? (
          <EmptyState
            compact
            title="No endpoint data yet"
            body={
              monitoring
                ? `${scopeLabel} has not shipped any request logs in the last ${rangeLabel(hours)}.`
                : "Send some traffic through the gateway to populate this ranking."
            }
          />
        ) : (
          <Table minWidth={760}>
            <THead>
              <tr>
                <TH>Endpoint</TH>
                <TH align="right">Requests</TH>
                <TH align="right">Avg</TH>
                <TH align="right">p95</TH>
                <TH align="right">p99</TH>
                <TH align="right">Errors</TH>
                <TH align="right">Cache hit</TH>
              </tr>
            </THead>
            <TBody>
              {ranking.map((endpoint, index) => (
                <TR key={endpoint.endpoint}>
                  <TD>
                    <div className="flex items-center gap-2.5">
                      <span className="w-5 font-mono text-[11px] text-faint">{index + 1}</span>
                      <span className="font-mono text-[13px] text-ink">{endpoint.endpoint}</span>
                    </div>
                  </TD>
                  <TD mono align="right">
                    {endpoint.count.toLocaleString()}
                  </TD>
                  <TD mono align="right">
                    {formatMs(endpoint.avg_time)}
                  </TD>
                  <TD mono align="right" className={cn(endpoint.p95_time > 500 && "text-warn")}>
                    {formatMs(endpoint.p95_time)}
                  </TD>
                  <TD mono align="right" className={cn(endpoint.p99_time > 1000 && "text-signal")}>
                    {formatMs(endpoint.p99_time)}
                  </TD>
                  <TD mono align="right" className={cn(endpoint.errors > 0 && "text-signal")}>
                    {endpoint.errors} ({formatPercent(endpoint.error_rate, 0)})
                  </TD>
                  <TD mono align="right">
                    {formatPercent(endpoint.cache_hit_rate, 0)}
                  </TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Panel>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <Panel title="Top endpoints" description="By request count" icon={<ListChecks className="h-4 w-4" />} flush>
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : topEndpoints.length === 0 ? (
            <EmptyState compact title="No endpoint data yet" />
          ) : (
            <Table minWidth={480}>
              <THead>
                <tr>
                  <TH>Endpoint</TH>
                  <TH align="right">Requests</TH>
                  <TH align="right">Avg</TH>
                  <TH align="right">Cache hit</TH>
                </tr>
              </THead>
              <TBody>
                {topEndpoints.map((endpoint) => (
                  <TR key={endpoint.endpoint}>
                    <TD mono className="max-w-[260px] truncate text-ink">
                      {endpoint.endpoint}
                    </TD>
                    <TD mono align="right">
                      {endpoint.count.toLocaleString()}
                    </TD>
                    <TD mono align="right">
                      {formatMs(endpoint.avg_time)}
                    </TD>
                    <TD mono align="right">
                      {formatPercent(endpoint.cache_hit_rate, 0)}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </Panel>

        <Panel
          title="Recent requests"
          description={monitoring ? `Latest requests ${scopeLabel} served and calls it made` : "Latest traffic in this window"}
          flush
        >
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-9 w-full" />
              ))}
            </div>
          ) : recent.length === 0 ? (
            <EmptyState compact title="No recent traffic" />
          ) : (
            <ul className="divide-y divide-rule">
              {recent.slice(0, 10).map((request, index) => (
                <li key={`${request.created_at}-${index}`} className="flex items-center justify-between gap-3 px-5 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate font-mono text-[12px] text-ink">
                      <span className="text-faint">{request.method}</span> {request.endpoint}
                    </p>
                    <p className="mt-0.5 text-[11px] text-faint">{formatTime(request.created_at)}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {monitoring && <DirectionPill direction={request.direction} />}
                    {request.cache_hit && <Pill tone="emerald">hit</Pill>}
                    <StatusCodePill status={request.status_code} />
                    <span className="w-14 text-right font-mono text-[11px] text-faint">
                      {formatMs(request.response_time_ms, 0)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <div className="mt-4">
        <RequestLogExplorer hours={hours} service={service} />
      </div>
    </>
  )
}
