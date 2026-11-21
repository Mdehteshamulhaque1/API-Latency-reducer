"use client"

import * as React from "react"
import { Gauge, RefreshCw, ShieldAlert, Timer, User } from "lucide-react"

import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { MethodPill, Pill } from "@/components/ui/pill"
import { RANGE_OPTIONS, Segmented, rangeLabel } from "@/components/ui/segmented"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table"
import {
  apiRateLimitConfig,
  apiRateLimitEvents,
  apiRateLimitMe,
  type RateLimitConfig,
  type RateLimitEventSummary,
  type RateLimitUsage,
} from "@/lib/api"
import { MonitoredRateLimitsView } from "@/components/dashboard/monitored-rate-limits"
import { usePolling } from "@/lib/use-auth"
import { useMonitoredService } from "@/lib/use-service"
import { cn, formatDateTime, formatPercent, formatRelative, formatSeconds } from "@/lib/utils"

interface RateLimitData {
  config: RateLimitConfig
  me: RateLimitUsage
  events: RateLimitEventSummary
}

export default function RateLimitsPage() {
  const monitored = useMonitoredService()
  if (monitored.monitoring && monitored.service) {
    return <MonitoredRateLimitsView service={monitored.service} label={monitored.label} />
  }
  return <GatewayRateLimitsPage />
}

function GatewayRateLimitsPage() {
  const [hours, setHours] = React.useState(24)
  const loader = React.useCallback(async (): Promise<RateLimitData> => {
    const [config, me, events] = await Promise.all([
      apiRateLimitConfig(),
      apiRateLimitMe(),
      apiRateLimitEvents(hours, 50),
    ])
    return { config, me, events }
  }, [hours])
  const { data, loading, error, reload, updatedAt } = usePolling<RateLimitData>(loader, 15_000)

  const config = data?.config
  const me = data?.me
  const events = data?.events
  const initial = loading && !data
  const usedShare = me && me.limit > 0 ? (me.used / me.limit) * 100 : 0

  return (
    <>
      <PageHeader
        eyebrow="rate limiting"
        title="Rate limits"
        description="Token-bucket configuration, your own bucket, and the requests that were rejected with HTTP 429."
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
              label="Your bucket capacity"
              value={String(config?.capacity ?? 0)}
              hint={`${config?.your_tier ?? "user"} tier, refills in ${formatSeconds(config?.period_seconds ?? 0)}`}
              tone="indigo"
              icon={<Gauge className="h-4 w-4" />}
            />
            <StatCard
              label="Refill rate"
              value={`${(config?.refill_per_second ?? 0).toFixed(2)}/s`}
              hint={config?.enabled ? "limiter enabled" : "limiter disabled"}
              tone={config?.enabled ? "emerald" : "amber"}
              icon={<Timer className="h-4 w-4" />}
            />
            <StatCard
              label="Rejected (429)"
              value={(events?.rate_limited_requests ?? 0).toLocaleString()}
              hint={`${formatPercent(events?.rate_limited_percent ?? 0)} of ${(events?.total_requests ?? 0).toLocaleString()} requests, ${events?.scope === "all" ? "all users" : "your traffic"}`}
              tone={(events?.rate_limited_requests ?? 0) > 0 ? "amber" : "emerald"}
              icon={<ShieldAlert className="h-4 w-4" />}
            />
            <StatCard
              label="Your bucket"
              value={me ? `${me.remaining}/${me.limit}` : "—"}
              hint={me?.has_bucket ? `full again in ${formatSeconds(me.reset_in_seconds)}` : "no requests yet"}
              tone="cyan"
              icon={<User className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1.4fr]">
        <div className="space-y-4">
          <Panel title="Your token bucket" description={me?.identifier ?? "user bucket"} icon={<User className="h-4 w-4" />}>
            {initial ? (
              <Skeleton className="h-24 w-full" />
            ) : (
              <>
                <div className="flex items-end justify-between">
                  <p className="font-mono text-4xl tracking-tight text-ink">{me?.remaining ?? 0}</p>
                  <p className="text-xs text-faint">tokens left of {me?.limit ?? 0}</p>
                </div>
                <div className="mt-4 h-3 w-full overflow-hidden rounded bg-frost" role="img" aria-label="Bucket usage">
                  <div
                    className={cn("h-full rounded transition-[width]", usedShare > 80 ? "bg-warn/10" : "bg-steel/10")}
                    style={{ width: `${Math.min(100, usedShare)}%` }}
                  />
                </div>
                <p className="mt-2 text-[11px] text-faint">
                  Every request takes one token. Tokens come back continuously at the refill rate, so a short burst
                  is fine and a sustained flood is slowed to the average rate.
                </p>
                {me?.error && <Alert variant="default" className="mt-3">Redis unavailable: the limiter is failing open.</Alert>}
              </>
            )}
          </Panel>

          <Panel title="Tiers" description="Bucket size per class of caller, from the environment" flush>
            {initial ? (
              <div className="space-y-3 p-5">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-10 w-full" />
                ))}
              </div>
            ) : (
              <ul className="divide-y divide-rule">
                {(config?.tiers ?? []).map((tier) => (
                  <li key={tier.name} className="flex items-center justify-between gap-3 px-5 py-2.5">
                    <div className="min-w-0">
                      <p className="flex items-center gap-2 text-[13px] text-ink">
                        <span className="capitalize">{tier.name}</span>
                        {tier.name === config?.your_tier && <Pill tone="indigo">you</Pill>}
                      </p>
                      <p className="mt-0.5 truncate text-[11px] text-graphite">{tier.applies_to}</p>
                    </div>
                    <div className="shrink-0 text-right">
                      <p className="font-mono text-[13px] text-ink">
                        {tier.capacity.toLocaleString()} / {formatSeconds(tier.period_seconds)}
                      </p>
                      <p className="font-mono text-[11px] text-faint">{tier.policy}</p>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Configuration" description="Effective settings from the environment">
            {initial ? (
              <Skeleton className="h-32 w-full" />
            ) : (
              <dl className="space-y-2 text-sm">
                {[
                  ["Algorithm", config?.algorithm ?? "—"],
                  ["Identifier", config?.identifier_strategy ?? "—"],
                  ["Failure policy", config?.failure_policy ?? "—"],
                  ["Headers", (config?.headers ?? []).join(", ") || "—"],
                ].map(([label, value]) => (
                  <div key={label} className="flex flex-col gap-0.5 border-b border-rule pb-2 last:border-0">
                    <dt className="text-[12px] text-graphite">{label}</dt>
                    <dd className="text-ink">{value}</dd>
                  </div>
                ))}
                <div>
                  <dt className="text-[12px] text-graphite">Exempt paths</dt>
                  <dd className="mt-1 flex flex-wrap gap-1">
                    {(config?.excluded_paths ?? []).map((path) => (
                      <span key={path} className="rounded border border-rule bg-frost px-1.5 py-0.5 font-mono text-[10px] text-graphite">
                        {path}
                      </span>
                    ))}
                  </dd>
                </div>
              </dl>
            )}
          </Panel>
        </div>

        <Panel
          title="Rejected requests"
          description={`HTTP 429 responses in the last ${rangeLabel(hours)}`}
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
          ) : !events || events.events.length === 0 ? (
            <EmptyState compact icon={<ShieldAlert className="h-5 w-5" />} title="No rejected requests" body="Nobody hit the limit in this window." />
          ) : (
            <Table minWidth={640}>
              <THead>
                <tr>
                  <TH>Time</TH>
                  <TH>Request</TH>
                  <TH>Client</TH>
                  <TH>User</TH>
                  <TH>Correlation ID</TH>
                </tr>
              </THead>
              <TBody>
                {events.events.map((event) => (
                  <TR key={event.id}>
                    <TD className="whitespace-nowrap text-xs text-faint">{formatDateTime(event.created_at)}</TD>
                    <TD>
                      <div className="flex items-center gap-2">
                        <MethodPill method={event.method} />
                        <span className="max-w-[240px] truncate font-mono text-[13px] text-ink">{event.endpoint}</span>
                      </div>
                    </TD>
                    <TD mono className="text-graphite">{event.client_ip}</TD>
                    <TD>{event.user_id !== null ? <Pill tone="indigo">user {event.user_id}</Pill> : <Pill tone="zinc">anonymous</Pill>}</TD>
                    <TD mono className="max-w-[160px] truncate text-faint" title={event.correlation_id}>{event.correlation_id}</TD>
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
