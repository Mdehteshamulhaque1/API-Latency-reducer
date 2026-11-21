"use client"

import * as React from "react"
import { Activity, Globe, RefreshCw, ShieldAlert } from "lucide-react"

import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { Panel } from "@/components/ui/panel"
import { MethodPill } from "@/components/ui/pill"
import { RANGE_OPTIONS, Segmented, rangeLabel } from "@/components/ui/segmented"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table"
import { apiRateLimitEvents, type RateLimitEventSummary } from "@/lib/api"
import { usePolling } from "@/lib/use-auth"
import { cn, formatDateTime, formatPercent, formatRelative } from "@/lib/utils"

function tally<T>(items: T[], key: (item: T) => string, limit = 5): { name: string; count: number }[] {
  const counts = new Map<string, number>()
  for (const item of items) counts.set(key(item), (counts.get(key(item)) ?? 0) + 1)
  return Array.from(counts.entries())
    .map(([name, count]) => ({ name, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, limit)
}

/**
 * Rate-limits page while a monitored service is selected: the HTTP 429
 * responses that service returned to its own callers (its login and register
 * limiter), grouped by route and by client, from its shipped request log.
 */
export function MonitoredRateLimitsView({ service, label }: { service: string; label: string }) {
  const [hours, setHours] = React.useState(24)
  const loader = React.useCallback(() => apiRateLimitEvents(hours, 100, { service }), [hours, service])
  const { data, loading, error, reload, updatedAt } = usePolling<RateLimitEventSummary>(loader, 15_000)

  const events = React.useMemo(() => data?.events ?? [], [data])
  const byEndpoint = React.useMemo(() => tally(events, (event) => `${event.method} ${event.endpoint}`), [events])
  const byClient = React.useMemo(() => tally(events, (event) => event.client_ip), [events])
  const initial = loading && !data

  return (
    <>
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="mono-label">rate limiting</p>
          <h1 className="text-[28px] font-semibold leading-tight tracking-[-0.01em] text-ink">{label} rate limits</h1>
          <p className="mt-1.5 max-w-xl text-sm text-graphite">
            Requests {label} rejected with HTTP 429, who sent them and which routes they hit. {label} limits sign-in
            and registration attempts per client address.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Segmented value={hours} onChange={setHours} options={RANGE_OPTIONS} ariaLabel="Time range" />
          <Button variant="outline" size="sm" onClick={reload} disabled={loading} className="gap-2">
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </Button>
        </div>
      </div>

      {error && (
        <Alert variant="destructive" className="mb-6">
          {error}
        </Alert>
      )}

      <div className="housing housing-row grid sm:grid-cols-3">
        {initial ? (
          Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-[120px]" />)
        ) : (
          <>
            <StatCard
              label="Rejected (429)"
              value={(data?.rate_limited_requests ?? 0).toLocaleString()}
              hint={`last ${rangeLabel(hours)}`}
              tone={(data?.rate_limited_requests ?? 0) > 0 ? "amber" : "emerald"}
              icon={<ShieldAlert className="h-4 w-4" />}
            />
            <StatCard
              label="Share of traffic"
              value={formatPercent(data?.rate_limited_percent ?? 0)}
              hint={`of ${(data?.total_requests ?? 0).toLocaleString()} requests ${label} served`}
              tone="indigo"
              icon={<Activity className="h-4 w-4" />}
            />
            <StatCard
              label="Clients limited"
              value={byClient.length.toLocaleString()}
              hint={byClient[0] ? `most: ${byClient[0].name} (${byClient[0].count})` : "nobody hit the limit"}
              tone="cyan"
              icon={<Globe className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1.4fr]">
        <div className="space-y-4">
          <Panel title="By route" description="Routes that returned 429 most often" flush>
            {initial ? (
              <div className="space-y-3 p-5">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-8 w-full" />
                ))}
              </div>
            ) : byEndpoint.length === 0 ? (
              <EmptyState compact title="No rejections" />
            ) : (
              <ul className="divide-y divide-rule">
                {byEndpoint.map((item) => (
                  <li key={item.name} className="flex items-center justify-between gap-3 px-5 py-2.5">
                    <span className="truncate font-mono text-[12px] text-ink">{item.name}</span>
                    <span className="shrink-0 font-mono text-[12px] text-graphite">{item.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
          <Panel title="By client" description="Addresses that were throttled" flush>
            {initial ? (
              <div className="space-y-3 p-5">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-8 w-full" />
                ))}
              </div>
            ) : byClient.length === 0 ? (
              <EmptyState compact title="No clients throttled" />
            ) : (
              <ul className="divide-y divide-rule">
                {byClient.map((item) => (
                  <li key={item.name} className="flex items-center justify-between gap-3 px-5 py-2.5">
                    <span className="truncate font-mono text-[12px] text-ink">{item.name}</span>
                    <span className="shrink-0 font-mono text-[12px] text-graphite">{item.count}</span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>

        <Panel
          title="Rejected requests"
          description={`HTTP 429 responses from ${label} in the last ${rangeLabel(hours)}`}
          icon={<ShieldAlert className="h-4 w-4" />}
          actions={updatedAt ? <span className="mono-label">updated {formatRelative(updatedAt)}</span> : undefined}
          flush
        >
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : events.length === 0 ? (
            <EmptyState
              compact
              icon={<ShieldAlert className="h-5 w-5" />}
              title="No rejected requests"
              body={`${label} did not throttle anyone in this window.`}
            />
          ) : (
            <Table minWidth={640}>
              <THead>
                <tr>
                  <TH>Time</TH>
                  <TH>Request</TH>
                  <TH>Client</TH>
                  <TH>Correlation ID</TH>
                </tr>
              </THead>
              <TBody>
                {events.map((event) => (
                  <TR key={event.id}>
                    <TD className="whitespace-nowrap text-xs text-faint" title={event.created_at}>
                      {formatDateTime(event.created_at)}
                    </TD>
                    <TD>
                      <div className="flex items-center gap-2">
                        <MethodPill method={event.method} />
                        <span className="max-w-[260px] truncate font-mono text-[13px] text-ink">{event.endpoint}</span>
                      </div>
                    </TD>
                    <TD mono className="text-graphite">
                      {event.client_ip}
                    </TD>
                    <TD mono className="max-w-[160px] truncate text-faint" title={event.correlation_id}>
                      {event.correlation_id}
                    </TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </Panel>
      </div>
    </>
  )
}
