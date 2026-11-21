"use client"

import * as React from "react"
import Link from "next/link"
import { RefreshCw } from "lucide-react"

import { LatencyChart } from "@/components/charts/latency-chart"
import { Sparkline } from "@/components/charts/sparkline"
import { CHART } from "@/components/charts/chart-theme"
import { DirectionPill } from "@/components/dashboard/service-switch"
import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { Pill, StatusCodePill, type PillTone } from "@/components/ui/pill"
import { Skeleton } from "@/components/ui/skeleton"
import {
  apiAnalyticsSummary,
  apiHealth,
  apiRules,
  type AnalyticsSummary,
  type CacheRule,
  type HealthResponse,
} from "@/lib/api"
import { useAuth, usePolling } from "@/lib/use-auth"
import { useMonitoredService } from "@/lib/use-service"
import { useViewAs } from "@/lib/use-view-as"
import { cn, formatMs, formatPercent, formatRelative, formatSeconds, formatTime, num } from "@/lib/utils"

const HOURS = 24

interface OverviewData {
  summary: AnalyticsSummary
  rules: CacheRule[]
  health: HealthResponse | null
}

async function loadOverview(service: string | null): Promise<OverviewData> {
  const [summary, rules, health] = await Promise.all([
    apiAnalyticsSummary(HOURS, { service: service ?? undefined }),
    apiRules(),
    apiHealth().catch(() => null),
  ])
  return { summary, rules, health }
}

/** One readout in the KPI housing. */
function Readout({
  label,
  value,
  hint,
  tone = "ink",
  spark,
  sparkColor,
  id,
}: {
  label: string
  value: string
  hint?: string
  tone?: "ink" | "relay" | "signal" | "warn"
  spark?: number[]
  sparkColor?: string
  id: string
}) {
  const toneClass = { ink: "text-ink", relay: "text-relay", signal: "text-signal", warn: "text-warn" }[tone]
  return (
    <div className="min-w-0 px-5 py-4">
      <p className="text-[12px] text-graphite">{label}</p>
      <p className={cn("mt-2 font-mono text-[30px] font-medium leading-none tracking-tight", toneClass)}>{value}</p>
      {hint && <p className="mt-2 truncate text-[12px] text-faint">{hint}</p>}
      <div className="mt-3 h-9">
        {spark && spark.length > 1 && <Sparkline id={id} values={spark} color={sparkColor} />}
      </div>
    </div>
  )
}

function healthTone(value: string | undefined): PillTone {
  if (value === "healthy") return "emerald"
  if (value === undefined) return "zinc"
  return "amber"
}

export default function DashboardPage() {
  const auth = useAuth()
  const monitored = useMonitoredService()
  const service = monitored.service
  const loader = React.useCallback(() => loadOverview(service), [service])
  const { data, loading, error, reload, updatedAt } = usePolling<OverviewData>(
    loader,
    monitored.loading ? null : 30_000,
  )
  const scopeLabel = monitored.label
  const viewedUser = useViewAs().user
  // The service feed (in/out counts) covers the whole service, so it is hidden while viewing one user.
  const monitoring = monitored.monitoring && !viewedUser

  const summary = data?.summary
  // While monitoring, only the rules written for that service's proxied paths are its rules.
  const rules = React.useMemo(() => {
    const all = data?.rules ?? []
    return service ? all.filter((rule) => rule.endpoint_pattern.startsWith(`/proxy/${service}/`)) : all
  }, [data, service])
  const health = data?.health ?? null
  const initial = loading && !data

  const enabledRules = rules.filter((rule) => rule.enabled)
  const hitRate = num(summary?.cache_hit_rate)
  const errorRate = num(summary?.error_rate)
  const series = summary?.latency_series ?? []
  const latencySpark = series.map((point) => point.avg_response_time_ms)
  const requestSpark = series.map((point) => point.request_count)
  const errorSpark = series.map((point) => point.error_count)
  const suggestions = (summary?.optimization_suggestions ?? []).slice(0, 3)
  const recent = (summary?.recent_requests ?? []).slice(0, 6)

  const services = [
    { label: "API", value: health?.status },
    { label: "Database", value: health?.database },
    { label: "Redis", value: health?.redis },
  ]

  return (
    <>
      <PageHeader
        title="Overview"
        description={
          viewedUser
            ? `${viewedUser.label}: requests this user made to the gateway in the last 24 hours.`
            : monitoring
              ? `${scopeLabel}: every request it served and every call it made in the last 24 hours, as shipped to this gateway.`
              : "Traffic, latency, caching and service health over the last 24 hours."
        }
        actions={
          <>
            {updatedAt && (
              <span className="hidden text-[12px] text-graphite sm:inline">Updated {formatRelative(updatedAt)}</span>
            )}
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

      {/* Health strip */}
      <div className="mb-4 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm">
        {services.map((item) => (
          <div key={item.label} className="flex items-center gap-2 text-ink">
            <span>{item.label}</span>
            <Pill tone={error && !health ? "red" : healthTone(item.value)} dot>
              {initial ? "checking" : item.value ?? "unreachable"}
            </Pill>
          </div>
        ))}
        {monitoring && monitored.selected && (
          <div className="flex items-center gap-2 text-ink">
            <span>{scopeLabel} feed</span>
            <Pill tone={monitored.selected.last_seen ? "emerald" : "zinc"} dot>
              {monitored.selected.last_seen ? `last seen ${formatRelative(Date.parse(monitored.selected.last_seen))}` : "no data"}
            </Pill>
            <span className="font-mono text-[12px] text-faint">
              {monitored.selected.inbound.toLocaleString()} in / {monitored.selected.outbound.toLocaleString()} out
            </span>
          </div>
        )}
        {health?.version && <span className="ml-auto font-mono text-[12px] text-faint">v{health.version}</span>}
      </div>

      {/* KPI housing: one frame, four readouts divided by rules */}
      {initial ? (
        <Skeleton className="h-[148px] w-full" />
      ) : (
        <div className="housing housing-row grid sm:grid-cols-2 lg:grid-cols-4">
          <Readout
            id="requests"
            label="Requests"
            value={num(summary?.total_requests).toLocaleString()}
            hint={`${num(summary?.request_rate_per_minute).toFixed(2)} per minute`}
            spark={requestSpark}
            sparkColor={CHART.ok}
          />
          <Readout
            id="latency"
            label="Average latency"
            value={formatMs(num(summary?.avg_response_time_ms))}
            hint={`p50 ${formatMs(num(summary?.overall_p50_response_time_ms), 0)}, p95 ${formatMs(
              num(summary?.overall_p95_response_time_ms),
              0,
            )}, p99 ${formatMs(num(summary?.overall_p99_response_time_ms), 0)}`}
            spark={latencySpark}
            sparkColor={CHART.avg}
          />
          {monitoring ? (
            <Readout
              id="outbound"
              label="Outbound calls"
              value={num(monitored.selected?.outbound).toLocaleString()}
              hint={`${num(monitored.selected?.inbound).toLocaleString()} requests served`}
              tone="relay"
            />
          ) : (
            <Readout
              id="cache"
              label="Cache hit rate"
              value={formatPercent(hitRate)}
              hint="Responses served from Redis"
              tone="relay"
            />
          )}
          <Readout
            id="errors"
            label="Error rate"
            value={formatPercent(errorRate)}
            hint={`${num(summary?.total_errors).toLocaleString()} errors, ${num(summary?.rate_limited_requests).toLocaleString()} rate limited`}
            tone={errorRate > 1 ? "signal" : "ink"}
            spark={errorSpark}
            sparkColor={CHART.error}
          />
        </div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.5fr_1fr]">
        <Panel
          title="Latency over time"
          description="Average response time per bucket"
          actions={
            <Link href="/dashboard/analytics" className="text-[13px] text-graphite underline-offset-4 hover:text-ink hover:underline">
              Open analytics
            </Link>
          }
        >
          {initial ? <Skeleton className="h-[240px] w-full" /> : <LatencyChart data={series} />}
        </Panel>

        <Panel title="Slowest endpoint" description="Highest average latency in the window">
          {initial ? (
            <Skeleton className="h-[240px] w-full" />
          ) : summary?.slowest_endpoint ? (
            <div className="flex h-[240px] flex-col justify-between">
              <div>
                <p className="break-all font-mono text-[13px] text-ink">{summary.slowest_endpoint}</p>
                <p className="mt-3 font-mono text-4xl font-medium tracking-tight text-signal">
                  {formatMs(num(summary.slowest_response_time_ms))}
                </p>
                <p className="mt-1 text-[12px] text-graphite">average response time</p>
              </div>
              <ol className="divide-y divide-rule border-t border-rule">
                {(summary.slow_endpoint_ranking ?? []).slice(0, 3).map((endpoint, index) => (
                  <li key={endpoint.endpoint} className="flex items-center justify-between gap-3 py-1.5 text-[12px]">
                    <span className="flex min-w-0 items-center gap-2">
                      <span className="font-mono text-faint">{index + 1}</span>
                      <span className="truncate font-mono text-ink">{endpoint.endpoint}</span>
                    </span>
                    <span className="shrink-0 font-mono text-graphite">p95 {formatMs(endpoint.p95_time, 0)}</span>
                  </li>
                ))}
              </ol>
            </div>
          ) : (
            <EmptyState
              title="No traffic yet"
              body={
                monitoring
                  ? `Latency rankings appear once ${scopeLabel} ships request logs to this gateway.`
                  : "Latency rankings appear once requests flow through the gateway."
              }
            />
          )}
        </Panel>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Panel
          title={monitoring ? `${scopeLabel} cache rules` : "Cache rules"}
          description={`${enabledRules.length} enabled of ${rules.length}`}
          actions={
            <Link href="/dashboard/rules" className="text-[13px] text-graphite underline-offset-4 hover:text-ink hover:underline">
              {auth.canEdit ? "Manage rules" : "View rules"}
            </Link>
          }
          flush
        >
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : rules.length === 0 ? (
            <EmptyState
              compact
              title="No cache rules yet"
              body={monitoring ? `Add a rule for /proxy/${service}/... to cache one of ${scopeLabel}'s routes.` : "Nothing is cached until a rule matches a path."}
            />
          ) : (
            <ul className="divide-y divide-rule">
              {[...rules]
                .sort((a, b) => Number(b.enabled) - Number(a.enabled) || b.priority - a.priority)
                .slice(0, 6)
                .map((rule) => (
                  <li key={rule.id} className="flex items-center justify-between gap-3 px-5 py-2.5">
                    <div className="min-w-0">
                      <p className="truncate font-mono text-[12px] text-ink">{rule.endpoint_pattern}</p>
                      <p className="mt-0.5 text-[11px] text-graphite">
                        TTL {formatSeconds(rule.ttl)}, priority {rule.priority}
                      </p>
                    </div>
                    <Pill tone={rule.enabled ? "emerald" : "zinc"}>{rule.enabled ? "on" : "off"}</Pill>
                  </li>
                ))}
            </ul>
          )}
        </Panel>

        <Panel
          title="Recent requests"
          description={monitoring ? `Latest requests ${scopeLabel} served and calls it made` : "Latest traffic through the gateway"}
          flush
        >
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-9 w-full" />
              ))}
            </div>
          ) : recent.length === 0 ? (
            <EmptyState compact title="No recent traffic" />
          ) : (
            <ul className="divide-y divide-rule">
              {recent.map((request, index) => (
                <li key={`${request.created_at}-${index}`} className="flex items-center justify-between gap-3 px-5 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate font-mono text-[12px] text-ink">
                      <span className="text-graphite">{request.method}</span> {request.endpoint}
                    </p>
                    <p className="mt-0.5 text-[11px] text-graphite">{formatTime(request.created_at)}</p>
                  </div>
                  <div className="flex shrink-0 items-center gap-1.5">
                    {monitoring && <DirectionPill direction={request.direction} />}
                    {request.cache_hit && <Pill tone="emerald">hit</Pill>}
                    <StatusCodePill status={request.status_code} />
                    <span className="w-12 text-right font-mono text-[11px] text-graphite">
                      {formatMs(request.response_time_ms, 0)}
                    </span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel title="Suggestions" description="Endpoints worth a look" flush>
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 2 }).map((_, index) => (
                <Skeleton key={index} className="h-12 w-full" />
              ))}
            </div>
          ) : suggestions.length === 0 ? (
            <EmptyState compact title="Nothing to flag" body="No endpoint crosses the thresholds right now." />
          ) : (
            <ul className="divide-y divide-rule">
              {suggestions.map((suggestion, index) => (
                <li key={`${suggestion.title}-${index}`} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-2">
                    <p className="truncate text-sm text-ink">{suggestion.title}</p>
                    <Pill tone={suggestion.severity === "high" ? "red" : suggestion.severity === "medium" ? "amber" : "zinc"}>
                      {suggestion.severity}
                    </Pill>
                  </div>
                  <p className="mt-1 line-clamp-2 text-[12px] text-graphite">{suggestion.action}</p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>
    </>
  )
}
