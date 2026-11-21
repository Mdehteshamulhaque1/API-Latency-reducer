"use client"

import * as React from "react"
import Link from "next/link"
import { ArrowUpRight, Database, Eraser, Lightbulb, RefreshCw, SlidersHorizontal, Sparkles } from "lucide-react"

import { CacheChart } from "@/components/charts/cache-chart"
import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { Pill, type PillTone } from "@/components/ui/pill"
import { RANGE_OPTIONS, Segmented, rangeLabel } from "@/components/ui/segmented"
import { Select } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Switch } from "@/components/ui/switch"
import {
  apiCacheInvalidate,
  apiCacheRecommendations,
  apiCacheStats,
  apiRules,
  type CacheRecommendation,
  type CacheRecommendationReport,
  type CacheRule,
  type CacheStats,
} from "@/lib/api"
import { MonitoredCacheView } from "@/components/dashboard/monitored-cache"
import { useAuth, usePolling } from "@/lib/use-auth"
import { useMonitoredService } from "@/lib/use-service"
import { cn, formatPercent, formatRelative, formatSeconds } from "@/lib/utils"

const KIND_TONE: Record<CacheRecommendation["kind"], PillTone> = {
  cache: "emerald",
  tune: "amber",
  do_not_cache: "red",
  keep: "zinc",
}

const KIND_LABEL: Record<CacheRecommendation["kind"], string> = {
  cache: "cache candidate",
  tune: "tune rule",
  do_not_cache: "do not cache",
  keep: "working",
}

interface CachePageData {
  stats: CacheStats
  rules: CacheRule[]
}

async function loadCache(): Promise<CachePageData> {
  const [stats, rules] = await Promise.all([apiCacheStats(), apiRules()])
  return { stats, rules }
}

function Recommendations({ hours, service }: { hours: number; service?: string }) {
  const [narrative, setNarrative] = React.useState(false)
  const loader = React.useCallback(
    () => apiCacheRecommendations(hours, narrative, { service }),
    [hours, narrative, service],
  )
  const { data, loading, error, reload } = usePolling<CacheRecommendationReport>(loader, null)

  return (
    <Panel
      title="Cache recommendations"
      description={`Advisory analysis of the last ${rangeLabel(hours)}; nothing is changed automatically`}
      icon={<Lightbulb className="h-4 w-4" />}
      actions={
        <>
          <label className="flex items-center gap-2 text-xs text-graphite">
            <Switch checked={narrative} onCheckedChange={setNarrative} label="Ask the model for a summary" />
            AI summary
          </label>
          <Button variant="outline" size="sm" onClick={reload} disabled={loading} className="gap-2">
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Analyse
          </Button>
        </>
      }
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
      ) : !data || data.recommendations.length === 0 ? (
        <EmptyState
          compact
          icon={<Lightbulb className="h-5 w-5" />}
          title="Nothing to recommend yet"
          body={`${data?.analysed_endpoints ?? 0} endpoints analysed. Recommendations need at least 20 requests per endpoint.`}
        />
      ) : (
        <>
          {data.explanation && (
            <div className="border-b border-rule px-5 py-4">
              <p className="mono-label mb-1.5 flex items-center gap-1.5">
                <Sparkles className="h-3 w-3 text-steel" />
                model summary, advisory
              </p>
              <p className="text-sm leading-relaxed text-ink">{data.explanation}</p>
            </div>
          )}
          <ul className="divide-y divide-rule">
            {data.recommendations.map((item) => (
              <li key={`${item.endpoint}-${item.kind}`} className="px-5 py-4">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-mono text-[13px] text-ink">{item.endpoint}</p>
                    <p className="mt-0.5 text-sm text-ink">{item.title}</p>
                  </div>
                  <Pill tone={KIND_TONE[item.kind]}>{KIND_LABEL[item.kind]}</Pill>
                </div>
                <p className="mt-2 text-xs leading-relaxed text-graphite">{item.reason}</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {Object.entries(item.evidence).map(([key, value]) => (
                    <span
                      key={key}
                      className="rounded border border-rule bg-frost px-1.5 py-0.5 font-mono text-[10px] text-graphite"
                    >
                      {key.replace(/_/g, " ")}: {String(value)}
                    </span>
                  ))}
                  {item.suggested_ttl_seconds && (
                    <span className="rounded border border-relay/40 bg-relay/10 px-1.5 py-0.5 font-mono text-[10px] text-relay">
                      suggested TTL {formatSeconds(item.suggested_ttl_seconds[0])} to{" "}
                      {formatSeconds(item.suggested_ttl_seconds[1])}
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ul>
          <p className="border-t border-rule px-5 py-3 text-[11px] text-faint">{data.note}</p>
        </>
      )}
    </Panel>
  )
}

export default function CachePage() {
  const monitored = useMonitoredService()
  if (monitored.monitoring && monitored.service) {
    return <MonitoredCacheOnly service={monitored.service} label={monitored.label} />
  }
  return <GatewayCachePage />
}

/** A monitored service has no Redis here; show its answer-cache efficiency instead. */
function MonitoredCacheOnly({ service, label }: { service: string; label: string }) {
  return (
    <MonitoredCacheView
      service={service}
      label={label}
      recommendations={(hours) => <Recommendations hours={hours} service={service} />}
    />
  )
}

function GatewayCachePage() {
  const auth = useAuth()
  const [hours, setHours] = React.useState(24)
  const loader = React.useCallback(() => loadCache(), [])
  const { data, loading, error, reload, updatedAt } = usePolling<CachePageData>(loader, 30_000)
  const [pattern, setPattern] = React.useState("")
  const [includeChat, setIncludeChat] = React.useState(false)
  const [busy, setBusy] = React.useState(false)
  const [message, setMessage] = React.useState<{ tone: "success" | "destructive"; text: string } | null>(null)

  const stats = data?.stats
  const rules = React.useMemo(() => data?.rules ?? [], [data])
  const initial = loading && !data

  async function invalidate() {
    setBusy(true)
    setMessage(null)
    try {
      const result = await apiCacheInvalidate({
        endpoint_pattern: pattern || undefined,
        include_chat: includeChat,
      })
      setMessage({ tone: "success", text: `Invalidated ${result.deleted} entries (${result.scope}).` })
      await reload()
    } catch (err) {
      setMessage({ tone: "destructive", text: err instanceof Error ? err.message : "Invalidation failed" })
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader
        eyebrow="cache"
        title="Response cache"
        description="Live counters from Redis, what is cached right now, and where caching would help next."
        actions={
          <>
            {updatedAt && <span className="mono-label hidden sm:inline">updated {formatRelative(updatedAt)}</span>}
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
      {stats && !stats.available && (
        <Alert variant="default" className="mb-6">
          Redis is unreachable. Caching fails open, so requests still succeed but nothing is served from cache.
        </Alert>
      )}

      <div className="housing housing-row grid sm:grid-cols-2 lg:grid-cols-4">
        {initial ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-[120px]" />)
        ) : (
          <>
            <StatCard
              label="Hit rate"
              value={formatPercent(stats?.cache_hit_rate ?? 0)}
              hint={`${(stats?.lookups ?? 0).toLocaleString()} lookups since counters reset`}
              tone="emerald"
              icon={<Database className="h-4 w-4" />}
            />
            <StatCard
              label="Hits / misses"
              value={`${(stats?.cache_hits ?? 0).toLocaleString()} / ${(stats?.cache_misses ?? 0).toLocaleString()}`}
              hint="process-wide counters in Redis"
              tone="cyan"
            />
            <StatCard
              label="Cached responses"
              value={(stats?.response_entries ?? 0).toLocaleString()}
              hint={`${(stats?.chat_entries ?? 0).toLocaleString()} LLM responses cached`}
              tone="indigo"
            />
            <StatCard
              label="Rules"
              value={`${stats?.enabled_rules ?? 0}/${stats?.total_rules ?? 0}`}
              hint={`default TTL ${formatSeconds(stats?.default_ttl_seconds ?? 0)}`}
              tone="indigo"
              icon={<SlidersHorizontal className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Panel title="Cache efficiency" description="Hits versus misses across all lookups">
          {initial ? (
            <Skeleton className="h-[240px] w-full" />
          ) : (
            <CacheChart totalRequests={stats?.lookups ?? 0} hitRate={stats?.cache_hit_rate ?? 0} />
          )}
        </Panel>

        <Panel
          title="Invalidate entries"
          description="Drop cached responses so the next request goes to the upstream"
          icon={<Eraser className="h-4 w-4" />}
          actions={
            <Button asChild variant="ghost" size="sm" className="gap-1.5 text-ink">
              <Link href="/dashboard/rules">
                Rules
                <ArrowUpRight className="h-3.5 w-3.5" />
              </Link>
            </Button>
          }
        >
          {auth.ready && !auth.canEdit ? (
            <EmptyState
              title="Operator or admin role required"
              body="Viewers can inspect the cache but cannot invalidate entries."
            />
          ) : (
            <div className="space-y-4">
              {message && <Alert variant={message.tone}>{message.text}</Alert>}
              <div className="space-y-2">
                <label className="mono-label block" htmlFor="invalidate-scope">
                  Scope
                </label>
                <Select id="invalidate-scope" value={pattern} onChange={(event) => setPattern(event.target.value)}>
                  <option value="">All cached responses</option>
                  {rules.map((rule) => (
                    <option key={rule.id} value={rule.endpoint_pattern}>
                      {rule.endpoint_pattern}, TTL {formatSeconds(rule.ttl)}
                    </option>
                  ))}
                </Select>
              </div>
              <label className="flex items-center justify-between gap-3 rounded border border-rule bg-frost p-3">
                <span>
                  <span className="block text-sm text-ink">Also clear LLM responses</span>
                  <span className="mt-0.5 block text-[11px] text-faint">
                    Exact-match chat cache entries will be regenerated on the next identical prompt.
                  </span>
                </span>
                <Switch checked={includeChat} onCheckedChange={setIncludeChat} label="Include LLM cache" />
              </label>
              <Button variant="primary" size="sm" onClick={invalidate} disabled={busy || !stats?.available} className="gap-2">
                <Eraser className="h-3.5 w-3.5" />
                {busy ? "Invalidating…" : "Invalidate now"}
              </Button>
              <p className="text-[11px] leading-relaxed text-faint">
                Entries also expire on their own when their rule&apos;s TTL elapses. Rate-limit buckets and
                sessions are never touched.
              </p>
            </div>
          )}
        </Panel>
      </div>

      <div className="mt-4 flex items-center justify-between">
        <p className="mono-label">analysis window</p>
        <Segmented value={hours} onChange={setHours} options={RANGE_OPTIONS} ariaLabel="Recommendation window" />
      </div>
      <div className="mt-2">
        <Recommendations hours={hours} />
      </div>

      {/* The shared AI answer cache (POST /api/v1/answers) and its per-user cost accounting. */}
      <MonitoredCacheView service={null} label={auth.isAdmin ? "gateway" : "your"} embedded />
    </>
  )
}
