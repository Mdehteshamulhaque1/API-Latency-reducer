"use client"

import * as React from "react"
import {
  Activity,
  Database,
  ExternalLink,
  RadioTower,
  RefreshCw,
  ServerCog,
  Wifi,
} from "lucide-react"

import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card } from "@/components/ui/card"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { Pill, type PillTone } from "@/components/ui/pill"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { API_BASE_URL, apiHealth, apiPing, type HealthResponse } from "@/lib/api"
import { usePolling } from "@/lib/use-auth"
import { cn, formatMs, formatRelative, formatTime } from "@/lib/utils"

const POLL_MS = 15_000
const HISTORY_LIMIT = 20

interface Probe {
  at: number
  status: string
  database: string
  redis: string
  pingMs: number | null
  error: string | null
}

interface StatusSnapshot {
  health: HealthResponse
  pingMs: number | null
}

async function probe(): Promise<StatusSnapshot> {
  const [health, ping] = await Promise.all([apiHealth(), apiPing().catch(() => null)])
  return { health, pingMs: ping?.round_trip_ms ?? null }
}

function tone(value: string | undefined): PillTone {
  if (value === "healthy") return "emerald"
  if (value === "degraded" || value === "unhealthy") return "amber"
  return "zinc"
}

function isHealthy(value: string | undefined): boolean {
  return value === "healthy"
}

export default function StatusPage() {
  const loader = React.useCallback(() => probe(), [])
  const { data, loading, error, reload, updatedAt } = usePolling<StatusSnapshot>(loader, POLL_MS)
  const [history, setHistory] = React.useState<Probe[]>([])

  React.useEffect(() => {
    if (!updatedAt) return
    setHistory((current) => {
      const entry: Probe = data
        ? {
            at: updatedAt,
            status: data.health.status,
            database: data.health.database,
            redis: data.health.redis,
            pingMs: data.pingMs,
            error: null,
          }
        : { at: updatedAt, status: "unreachable", database: "—", redis: "—", pingMs: null, error }
      return [entry, ...current].slice(0, HISTORY_LIMIT)
    })
    // Record one history entry per completed poll.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [updatedAt])

  React.useEffect(() => {
    if (!error) return
    setHistory((current) => {
      const last = current[0]
      if (last && last.error === error && Date.now() - last.at < POLL_MS / 2) return current
      return [
        { at: Date.now(), status: "unreachable", database: "—", redis: "—", pingMs: null, error },
        ...current,
      ].slice(0, HISTORY_LIMIT)
    })
  }, [error])

  const health = data?.health ?? null
  const initial = loading && !data
  const uptimeShare = history.length
    ? (history.filter((entry) => entry.status === "healthy").length / history.length) * 100
    : null

  const services = [
    { label: "API", value: error && !health ? "unreachable" : health?.status, icon: Activity, hint: "overall status" },
    { label: "Database", value: health?.database, icon: Database, hint: "SELECT 1 via SQLAlchemy" },
    { label: "Redis", value: health?.redis, icon: RadioTower, hint: "PING via redis.asyncio" },
  ]

  return (
    <>
      <PageHeader
        eyebrow="observability"
        title="System status"
        description="Live probes of the API, its database, and the Redis cache. Redis failing open keeps requests flowing even when it is down."
        actions={
          <>
            {updatedAt && <span className="mono-label hidden sm:inline">checked {formatRelative(updatedAt)}</span>}
            <Button variant="outline" size="sm" onClick={reload} disabled={loading} className="gap-2">
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
              Check now
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
              label="API"
              value={health?.status ?? "unreachable"}
              hint={health ? `v${health.version}` : API_BASE_URL}
              tone={isHealthy(health?.status) ? "emerald" : "amber"}
              icon={<ServerCog className="h-4 w-4" />}
            />
            <StatCard
              label="Database"
              value={health?.database ?? "—"}
              hint="query probe"
              tone={isHealthy(health?.database) ? "emerald" : "amber"}
              icon={<Database className="h-4 w-4" />}
            />
            <StatCard
              label="Redis"
              value={health?.redis ?? "—"}
              hint="cache + rate limits"
              tone={isHealthy(health?.redis) ? "emerald" : "amber"}
              icon={<RadioTower className="h-4 w-4" />}
            />
            <StatCard
              label="Ping round trip"
              value={data?.pingMs !== null && data?.pingMs !== undefined ? formatMs(data.pingMs, 0) : "—"}
              hint="browser GET /api/v1/ping"
              tone="cyan"
              icon={<Wifi className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <Panel title="Service checks" description="Results from GET /api/v1/health" flush>
          <ul className="divide-y divide-rule">
            {services.map((service) => (
              <li key={service.label} className="flex items-center justify-between gap-3 px-5 py-3.5">
                <span className="flex items-center gap-3">
                  <service.icon className="h-4 w-4 text-faint" />
                  <span>
                    <span className="block text-sm text-ink">{service.label}</span>
                    <span className="block text-[11px] text-faint">{service.hint}</span>
                  </span>
                </span>
                <Pill tone={initial ? "zinc" : tone(service.value)} dot>
                  {initial ? "checking" : service.value ?? "unknown"}
                </Pill>
              </li>
            ))}
          </ul>
          <div className="border-t border-rule px-5 py-4">
            <p className="text-xs leading-relaxed text-graphite">
              Polling every {POLL_MS / 1000}s while this tab is visible. Backend origin:{" "}
              <span className="font-mono text-ink">{API_BASE_URL}</span>
            </p>
            <Button
              variant="outline"
              size="sm"
              className="mt-3 gap-2"
              onClick={() => window.open(`${API_BASE_URL}/metrics`, "_blank", "noopener")}
            >
              Prometheus metrics
              <ExternalLink className="h-3.5 w-3.5" />
            </Button>
          </div>
        </Panel>

        <Panel
          title="Probe history"
          description={
            uptimeShare === null
              ? "This session only"
              : `${uptimeShare.toFixed(0)}% of the last ${history.length} probes healthy`
          }
          flush
        >
          {history.length === 0 ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-9 w-full" />
              ))}
            </div>
          ) : (
            <>
              <div className="flex gap-1 px-5 pt-4" aria-hidden>
                {[...history].reverse().map((entry) => (
                  <span
                    key={entry.at}
                    title={`${formatTime(entry.at)}, ${entry.status}`}
                    className={cn(
                      "h-6 flex-1 rounded-sm",
                      entry.status === "healthy"
                        ? "bg-relay/10"
                        : entry.status === "unreachable"
                          ? "bg-signal/10"
                          : "bg-warn/10",
                    )}
                  />
                ))}
              </div>
              <ul className="mt-3 max-h-[320px] divide-y divide-rule overflow-y-auto">
                {history.map((entry) => (
                  <li key={entry.at} className="flex items-center justify-between gap-3 px-5 py-2.5 text-xs">
                    <span className="font-mono text-faint">{formatTime(entry.at)}</span>
                    <span className="flex items-center gap-1.5">
                      <Pill tone={entry.status === "unreachable" ? "red" : tone(entry.status)} dot>
                        {entry.status}
                      </Pill>
                      {entry.error ? (
                        <span className="max-w-[200px] truncate text-signal">{entry.error}</span>
                      ) : (
                        <>
                          <Pill tone={tone(entry.database)}>db</Pill>
                          <Pill tone={tone(entry.redis)}>redis</Pill>
                        </>
                      )}
                      <span className="w-14 text-right font-mono text-faint">
                        {entry.pingMs !== null ? formatMs(entry.pingMs, 0) : "—"}
                      </span>
                    </span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Panel>
      </div>

      <Card className="mt-4 p-5">
        <h2 className="text-sm font-medium text-ink">What &ldquo;degraded&rdquo; means</h2>
        <p className="mt-1 text-xs leading-relaxed text-graphite">
          The API reports degraded when either the database or Redis probe fails. Redis is designed to fail open:
          caching and rate limiting are skipped, but authenticated requests still succeed. A database failure
          affects auth, rules, and analytics.
        </p>
      </Card>
    </>
  )
}
