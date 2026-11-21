"use client"

import * as React from "react"
import { ChevronDown, ChevronUp, Coins, Database, Globe, HardDrive, MessageSquare, RefreshCw, TrendingUp, Users, Zap } from "lucide-react"

import { CacheChart } from "@/components/charts/cache-chart"
import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { Panel } from "@/components/ui/panel"
import { Pill, type PillTone } from "@/components/ui/pill"
import { RANGE_OPTIONS, Segmented, rangeLabel, type SegmentedOption } from "@/components/ui/segmented"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table"
import {
  apiAnswersCache,
  apiAnswersCosts,
  apiAnswersRecent,
  apiAnswersStats,
  apiAnswersTop,
  apiAnswersUsers,
  type AnswerLogItem,
  type AnswerStats,
  type CacheOverview,
  type CostAnalytics,
  type TopQuestion,
  type UserQueryStats,
} from "@/lib/api"
import { usePolling } from "@/lib/use-auth"
import { cn, formatMs, formatPercent, formatRelative, formatSeconds, formatTime } from "@/lib/utils"

const RECENT_LIMIT = 50
const TOP_LIMIT = 10
const USERS_LIMIT = 25

const SOURCE_LABELS: Record<string, string> = {
  wikipedia: "Wikipedia",
  duckduckgo: "DuckDuckGo",
  wikidata: "Wikidata",
  web: "Web",
  gemini: "Gemini (own knowledge)",
}

const SOURCE_TONES: Record<string, PillTone> = {
  wikipedia: "indigo",
  duckduckgo: "cyan",
  wikidata: "zinc",
  web: "amber",
  gemini: "emerald",
}

type StatusChoice = "all" | "exact_hit" | "semantic_hit" | "miss" | "bypassed"

const STATUS_OPTIONS: ReadonlyArray<SegmentedOption<StatusChoice>> = [
  { value: "all", label: "all" },
  { value: "exact_hit", label: "exact" },
  { value: "semantic_hit", label: "semantic" },
  { value: "miss", label: "miss" },
  { value: "bypassed", label: "bypassed" },
]

interface MonitoredCacheData {
  stats: AnswerStats
  recent: AnswerLogItem[]
  recentTotal: number
  servedFrom: "redis" | "database"
  top: TopQuestion[]
  cache: CacheOverview
  costs: CostAnalytics
  users: UserQueryStats[]
  usersTotal: number
}

function sourceLabel(name: string | null): string {
  if (!name) return "—"
  return SOURCE_LABELS[name] ?? name
}

function usd(value: number, digits = 4): string {
  return `$${value.toFixed(digits)}`
}

function bytes(value: number): string {
  if (value >= 1_048_576) return `${(value / 1_048_576).toFixed(1)} MB`
  if (value >= 1024) return `${(value / 1024).toFixed(1)} KB`
  return `${value} B`
}

/** Clear visual labels for the cache outcome. */
function CacheStatusPill({ item }: { item: AnswerLogItem }) {
  if (item.status === "blocked") return <Pill tone="red">Blocked</Pill>
  if (item.status === "error") return <Pill tone="red">Error{item.error_code ? ` · ${item.error_code}` : ""}</Pill>
  switch (item.cache_status) {
    case "exact_hit":
      return <Pill tone="emerald">Exact Hit</Pill>
    case "semantic_hit":
      return <Pill tone="emerald">Semantic Hit{item.similarity !== null ? ` · ${Math.round(item.similarity * 100)}%` : ""}</Pill>
    case "bypassed":
      return <Pill tone="zinc">Cache Bypassed</Pill>
    default:
      if (!item.found) return <Pill tone="red">Not found</Pill>
      if (item.answered_by === "model") return <Pill tone="amber">Cache Miss · Gemini</Pill>
      return <Pill tone="amber">Cache Miss{item.compose_method ? ` · ${item.compose_method}` : ""}</Pill>
  }
}

function SourcePills({ item }: { item: AnswerLogItem }) {
  const names = Array.from(new Set(item.sources.map((s) => s.source ?? "web")))
  if (names.length === 0) return null
  return (
    <span className="flex flex-wrap items-center gap-1">
      {names.map((name) => (
        <Pill key={name} tone={SOURCE_TONES[name] ?? "zinc"}>
          {sourceLabel(name)}
        </Pill>
      ))}
    </span>
  )
}

/** One asked question: question, outcome, tokens and cost, the answer (click to expand) and its sources. */
function AnswerRow({ item }: { item: AnswerLogItem }) {
  const [open, setOpen] = React.useState(false)
  return (
    <li className="px-5 py-3">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        className="flex w-full items-start justify-between gap-3 text-left"
        aria-expanded={open}
      >
        <div className="min-w-0">
          <p className="text-[13px] text-ink">{item.question}</p>
          <p className="mt-0.5 text-[11px] text-faint">
            {formatTime(item.created_at)}
            {item.end_user ? ` · ${item.end_user}` : ""}
            {item.cache_key ? ` · ${item.cache_key.replace("answers:q:", "cache ")}` : ""}
            {item.waited_for_generation ? " · waited for another request" : ""}
          </p>
          <p className="mt-0.5 font-mono text-[11px] text-faint">
            in {item.prompt_tokens} · out {item.completion_tokens} · emb {item.embedding_tokens} tokens · cost{" "}
            {usd(item.total_cost_usd, 6)}
            {item.saved_cost_usd > 0 ? ` · saved ~${usd(item.saved_cost_usd, 6)}` : ""}
            {item.cache_lookup_ms > 0 ? ` · lookup ${formatMs(item.cache_lookup_ms, 0)}` : ""}
            {item.llm_ms > 0 ? ` · model ${formatMs(item.llm_ms, 0)}` : ""}
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          <CacheStatusPill item={item} />
          <span className="w-14 text-right font-mono text-[11px] text-faint">{formatMs(item.latency_ms, 0)}</span>
          {open ? <ChevronUp className="h-3.5 w-3.5 text-faint" /> : <ChevronDown className="h-3.5 w-3.5 text-faint" />}
        </div>
      </button>
      {item.answer && (
        <div className={cn("mt-2 text-[12px] leading-relaxed text-graphite", !open && "line-clamp-2")}>{item.answer}</div>
      )}
      {open && (
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <SourcePills item={item} />
          {item.sources.map((source, index) => (
            <a
              key={`${source.url}-${index}`}
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="truncate text-[11px] text-graphite underline-offset-4 hover:text-ink hover:underline"
              title={source.url}
            >
              [{index + 1}] {source.title}
            </a>
          ))}
        </div>
      )}
    </li>
  )
}

/**
 * Cache page while a monitored service is selected. The service has no Redis
 * of its own; what it does have is the gateway's shared answer cache. This
 * view shows what the cache holds, every question with the answer it
 * received and its cost, the LLM-versus-embedding spend and estimated
 * savings, and per-user totals, from GET /api/v1/answers/*.
 */
export function MonitoredCacheView({
  service,
  label,
  recommendations,
  embedded = false,
}: {
  /** Monitored service name, or null for the gateway's own callers (admins see every account). */
  service: string | null
  label: string
  recommendations?: (hours: number) => React.ReactNode
  /** Render as a section inside another page (smaller heading) instead of as the page itself. */
  embedded?: boolean
}) {
  const [hours, setHours] = React.useState(1)
  const [endUserInput, setEndUserInput] = React.useState("")
  const [endUser, setEndUser] = React.useState("")
  const [status, setStatus] = React.useState<StatusChoice>("all")
  const loader = React.useCallback(async (): Promise<MonitoredCacheData> => {
    const serviceScope = { service: service ?? undefined }
    const scope = { ...serviceScope, endUser: endUser || undefined }
    const [stats, recent, top, cache, costs, users] = await Promise.all([
      apiAnswersStats(hours, scope),
      apiAnswersRecent(hours, RECENT_LIMIT, { ...scope, cacheStatus: status === "all" ? undefined : status }),
      apiAnswersTop(hours, TOP_LIMIT, scope),
      apiAnswersCache(hours, serviceScope),
      apiAnswersCosts(hours, scope),
      apiAnswersUsers(hours, USERS_LIMIT, 0, serviceScope),
    ])
    return {
      stats,
      recent: recent.items,
      recentTotal: recent.total,
      servedFrom: recent.served_from,
      top: top.items,
      cache,
      costs,
      users: users.items,
      usersTotal: users.total,
    }
  }, [hours, service, endUser, status])
  const { data, loading, error, reload, updatedAt } = usePolling<MonitoredCacheData>(loader, 30_000)

  const stats = data?.stats
  const cache = data?.cache
  const costs = data?.costs
  const recent = data?.recent ?? []
  const top = data?.top ?? []
  const users = data?.users ?? []
  const initial = loading && !data

  return (
    <>
      <div className={cn("flex flex-wrap items-start justify-between gap-4", embedded ? "mb-4 mt-8 border-t border-rule pt-6" : "mb-6")}>
        <div>
          <p className="mono-label">{embedded ? "shared answer cache" : "answer cache"}</p>
          {embedded ? (
            <h2 className="text-[20px] font-semibold leading-tight tracking-[-0.01em] text-ink">Shared answer cache</h2>
          ) : (
            <h1 className="text-[28px] font-semibold leading-tight tracking-[-0.01em] text-ink">{label} answer cache</h1>
          )}
          <p className="mt-1.5 max-w-xl text-sm text-graphite">
            One shared answer per question, reused by every {label} user; one record per request per user. Costs
            are estimates from the pricing tables, never provider billing.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <form
            onSubmit={(event) => {
              event.preventDefault()
              setEndUser(endUserInput.trim())
            }}
            className="flex items-center gap-1"
          >
            <Input
              value={endUserInput}
              onChange={(event) => setEndUserInput(event.target.value)}
              placeholder="end user, e.g. esone:42"
              className="h-8 w-44 text-[13px]"
              aria-label="End user"
            />
            <Button type="submit" variant="subtle" size="sm">
              Filter
            </Button>
          </form>
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

      {/* A. Shared answer cache overview */}
      <div className="housing housing-row grid sm:grid-cols-2 lg:grid-cols-4">
        {initial ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-[120px]" />)
        ) : (
          <>
            <StatCard
              label="Cached answers"
              value={(cache?.active_entries ?? 0).toLocaleString()}
              hint={`${bytes(cache?.bytes_used ?? 0)} in Redis, ~${cache?.expired_estimate ?? 0} expired, ${cache?.redis_available ? "live" : "Redis unavailable"}`}
              tone={cache?.redis_available ? "indigo" : "amber"}
              icon={<HardDrive className="h-4 w-4" />}
            />
            <StatCard
              label="Cache hit rate"
              value={formatPercent(stats?.cache_hit_rate ?? 0)}
              hint={`${stats?.exact_hits ?? 0} exact, ${stats?.semantic_hits ?? 0} semantic, ${stats?.crawled ?? 0} misses, ${stats?.bypassed ?? 0} bypassed`}
              tone="emerald"
              icon={<Database className="h-4 w-4" />}
            />
            <StatCard
              label="Lookup latency"
              value={formatMs(stats?.avg_cache_lookup_ms ?? 0)}
              hint={`hit ${formatMs(stats?.avg_latency_cached_ms ?? 0, 0)} vs miss ${formatMs(stats?.avg_latency_crawled_ms ?? 0, 0)} end to end`}
              tone="cyan"
              icon={<Zap className="h-4 w-4" />}
            />
            <StatCard
              label="Questions"
              value={(stats?.questions ?? 0).toLocaleString()}
              hint={`${(stats?.unique_questions ?? 0).toLocaleString()} distinct, ${(stats?.end_users ?? 0).toLocaleString()} end users, ${
                (stats?.errors ?? 0) + (stats?.blocked ?? 0)
              } failed or blocked`}
              tone="indigo"
              icon={<MessageSquare className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      {/* B. LLM cost analytics */}
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.3fr_1fr]">
        <Panel
          title="AI cost analytics"
          description={costs ? `${costs.currency}, prices as of ${costs.pricing_effective_date}. ${costs.cost_note}` : "Estimates from the pricing tables"}
          icon={<Coins className="h-4 w-4" />}
          flush
        >
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 6 }).map((_, index) => (
                <Skeleton key={index} className="h-8 w-full" />
              ))}
            </div>
          ) : (
            <dl className="grid grid-cols-2 gap-x-6 gap-y-2 px-5 py-4 text-[13px] sm:grid-cols-3">
              {[
                ["Actual LLM cost", usd(costs?.llm_cost_usd ?? 0, 6)],
                ["Actual embedding cost", usd(costs?.embedding_cost_usd ?? 0, 6)],
                ["Total actual AI cost", usd(costs?.total_cost_usd ?? 0, 6)],
                ["Estimated saved by cache", `~${usd(costs?.saved_cost_usd ?? 0, 6)}`],
                ["LLM calls made", (costs?.llm_calls_made ?? 0).toLocaleString()],
                ["LLM calls avoided", (costs?.llm_calls_avoided ?? 0).toLocaleString()],
                ["Input tokens", (costs?.prompt_tokens ?? 0).toLocaleString()],
                ["Output tokens", (costs?.completion_tokens ?? 0).toLocaleString()],
                ["Embedding tokens", (costs?.embedding_tokens ?? 0).toLocaleString()],
                ["Avg cost per hit", usd(costs?.avg_cost_per_hit_usd ?? 0, 6)],
                ["Avg cost per miss", usd(costs?.avg_cost_per_miss_usd ?? 0, 6)],
                ["Hit vs miss latency", `${formatMs(costs?.avg_latency_hit_ms ?? 0, 0)} vs ${formatMs(costs?.avg_latency_miss_ms ?? 0, 0)}`],
              ].map(([k, v]) => (
                <div key={k} className="border-b border-rule pb-1.5 last:border-0">
                  <dt className="text-[11px] text-graphite">{k}</dt>
                  <dd className="font-mono text-ink">{v}</dd>
                </div>
              ))}
            </dl>
          )}
        </Panel>

        <Panel
          title="Cache efficiency"
          description={`Share of ${label} questions served from the shared cache`}
          actions={updatedAt ? <span className="mono-label">updated {formatRelative(updatedAt)}</span> : undefined}
        >
          {initial ? (
            <Skeleton className="h-[240px] w-full" />
          ) : (
            <CacheChart totalRequests={stats?.questions ?? 0} hitRate={stats?.cache_hit_rate ?? 0} />
          )}
        </Panel>
      </div>

      {/* C. Per-user analytics */}
      <Panel
        className="mt-4"
        title="Per-user query analytics"
        description={`Most active callers in the last ${rangeLabel(hours)}${data ? `, ${data.usersTotal} in total` : ""}. Savings are estimates.`}
        icon={<Users className="h-4 w-4" />}
        flush
      >
        {initial ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-9 w-full" />
            ))}
          </div>
        ) : users.length === 0 ? (
          <EmptyState compact title="No callers yet" />
        ) : (
          <Table minWidth={900}>
            <THead>
              <tr>
                <TH>User</TH>
                <TH align="right">Queries</TH>
                <TH align="right">Exact</TH>
                <TH align="right">Semantic</TH>
                <TH align="right">Misses</TH>
                <TH align="right">LLM calls</TH>
                <TH align="right">Tokens</TH>
                <TH align="right">Actual cost</TH>
                <TH align="right">Est. saved</TH>
                <TH align="right">Avg latency</TH>
              </tr>
            </THead>
            <TBody>
              {users.map((u) => (
                <TR key={u.user}>
                  <TD>
                    <button
                      type="button"
                      className="font-mono text-[12px] text-ink underline-offset-4 hover:underline"
                      onClick={() => {
                        if (u.end_user) {
                          setEndUserInput(u.end_user)
                          setEndUser(u.end_user)
                        }
                      }}
                      title={u.end_user ? "Filter the page to this user" : "Gateway account"}
                    >
                      {u.user}
                    </button>
                    <span className="ml-2 text-[11px] text-faint">{formatTime(u.last_seen)}</span>
                  </TD>
                  <TD mono align="right">{u.queries}</TD>
                  <TD mono align="right">{u.exact_hits}</TD>
                  <TD mono align="right">{u.semantic_hits}</TD>
                  <TD mono align="right">{u.misses + u.bypassed}</TD>
                  <TD mono align="right">{u.llm_calls}</TD>
                  <TD mono align="right">{(u.total_tokens + u.embedding_tokens).toLocaleString()}</TD>
                  <TD mono align="right">{usd(u.total_cost_usd, 6)}</TD>
                  <TD mono align="right">~{usd(u.saved_cost_usd, 6)}</TD>
                  <TD mono align="right">{formatMs(u.avg_latency_ms, 0)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Panel>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1.2fr]">
        <Panel title="Where answers came from" description="Misses by their first source; hits by match" icon={<Globe className="h-4 w-4" />} flush>
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-8 w-full" />
              ))}
            </div>
          ) : (stats?.by_source.length ?? 0) + (stats?.by_match.length ?? 0) === 0 ? (
            <EmptyState compact title="No answers yet" />
          ) : (
            <ul className="divide-y divide-rule">
              {(stats?.by_source ?? []).map((row) => (
                <li key={`source-${row.name}`} className="flex items-center justify-between gap-3 px-5 py-2.5">
                  <span className="flex items-center gap-2">
                    <Pill tone={SOURCE_TONES[row.name] ?? "zinc"}>{sourceLabel(row.name)}</Pill>
                    <span className="text-[12px] text-graphite">generated</span>
                  </span>
                  <span className="font-mono text-[12px] text-ink">{row.count.toLocaleString()}</span>
                </li>
              ))}
              {(stats?.by_match ?? []).map((row) => (
                <li key={`match-${row.name}`} className="flex items-center justify-between gap-3 px-5 py-2.5">
                  <span className="flex items-center gap-2">
                    <Pill tone="emerald">{row.name}</Pill>
                    <span className="text-[12px] text-graphite">cache match</span>
                  </span>
                  <span className="font-mono text-[12px] text-ink">{row.count.toLocaleString()}</span>
                </li>
              ))}
              {cache && (
                <li className="px-5 py-2.5 text-[11px] text-faint">
                  TTL {formatSeconds(cache.ttl_seconds)} ({formatSeconds(cache.volatile_ttl_seconds)} for time-sensitive questions), threshold{" "}
                  {cache.similarity_threshold}, {cache.expiry_policy}.
                </li>
              )}
            </ul>
          )}
        </Panel>

        <Panel title="Most asked" description={`Questions repeated most in the last ${rangeLabel(hours)}`} icon={<TrendingUp className="h-4 w-4" />} flush>
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-9 w-full" />
              ))}
            </div>
          ) : top.length === 0 ? (
            <EmptyState compact title="Nothing asked twice yet" />
          ) : (
            <ol className="divide-y divide-rule">
              {top.map((row, index) => (
                <li key={row.question_hash} className="flex items-start justify-between gap-3 px-5 py-2.5">
                  <div className="min-w-0">
                    <p className="truncate text-[13px] text-ink" title={row.question}>
                      <span className="mr-2 font-mono text-faint">{index + 1}</span>
                      {row.question}
                    </p>
                    <p className="mt-0.5 line-clamp-1 text-[11px] text-faint" title={row.last_answer}>
                      {row.last_answer}
                    </p>
                  </div>
                  <div className="flex shrink-0 flex-col items-end gap-1">
                    <span className="font-mono text-[12px] text-ink">{row.asked}×</span>
                    <span className="text-[11px] text-faint">
                      {row.cache_hits} cached · {formatMs(row.avg_latency_ms, 0)}
                    </span>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </Panel>
      </div>

      {/* D. Query-level details */}
      <Panel
        className="mt-4"
        title="Questions and answers"
        description={
          data
            ? `${data.recentTotal.toLocaleString()} in the last ${rangeLabel(hours)}, newest ${Math.min(RECENT_LIMIT, data.recent.length)} shown, read from ${data.servedFrom === "redis" ? "the Redis recent list" : "the database"}. Click a row for sources.`
            : "Newest questions with the answer each one received"
        }
        actions={<Segmented value={status} onChange={setStatus} options={STATUS_OPTIONS} ariaLabel="Cache status" />}
        flush
      >
        {initial ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-12 w-full" />
            ))}
          </div>
        ) : recent.length === 0 ? (
          <EmptyState
            compact
            title="No questions yet"
            body={`${label} has not forwarded any chat requests in the last ${rangeLabel(hours)}${status === "all" ? "" : " with this cache status"}.`}
          />
        ) : (
          <ul className="divide-y divide-rule">
            {recent.map((item) => (
              <AnswerRow key={item.id} item={item} />
            ))}
          </ul>
        )}
      </Panel>

      {recommendations && <div className="mt-4">{recommendations(hours)}</div>}
    </>
  )
}
