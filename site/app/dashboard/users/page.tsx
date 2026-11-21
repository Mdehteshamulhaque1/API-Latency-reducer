"use client"

import * as React from "react"
import Link from "next/link"
import { useRouter, useSearchParams } from "next/navigation"
import {
  Activity,
  ArrowLeft,
  Bot,
  Coins,
  Gauge,
  LayoutDashboard,
  MessageSquare,
  RefreshCw,
  Search,
  ShieldAlert,
  Timer,
  User,
  Users,
  Wallet,
} from "lucide-react"

import { LatencyChart } from "@/components/charts/latency-chart"
import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { MethodPill, Pill, StatusCodePill, type PillTone } from "@/components/ui/pill"
import { RANGE_OPTIONS, Segmented, rangeLabel, type SegmentedOption } from "@/components/ui/segmented"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table"
import {
  apiUserDetail,
  apiUsers,
  type AnswerLogItem,
  type UserDetail,
  type UserKind,
  type UserListItem,
  type UserListPage,
} from "@/lib/api"
import { useAuth, usePolling } from "@/lib/use-auth"
import { useViewAs } from "@/lib/use-view-as"
import { cn, formatDateTime, formatMs, formatPercent, formatRelative } from "@/lib/utils"

type KindChoice = "all" | UserKind

const KIND_OPTIONS: ReadonlyArray<SegmentedOption<KindChoice>> = [
  { value: "all", label: "all" },
  { value: "account", label: "accounts" },
  { value: "end_user", label: "service users" },
]

const ROLE_TONE: Record<string, PillTone> = { admin: "red", operator: "amber", viewer: "indigo", guest: "zinc" }

function inr(value: number): string {
  return `₹${value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function displayName(item: { username: string | null; key: string }): string {
  return item.username ?? item.key
}

function KindPill({ kind, role, service }: { kind: UserKind; role: string | null; service: string | null }) {
  if (kind === "end_user") return <Pill tone="cyan">{service ?? "service"} user</Pill>
  return <Pill tone={ROLE_TONE[role ?? ""] ?? "zinc"}>{role ?? "account"}</Pill>
}

function AnswerStatusPill({ item }: { item: AnswerLogItem }) {
  if (item.status === "blocked") return <Pill tone="red">blocked</Pill>
  if (item.status === "error") return <Pill tone="red">error</Pill>
  if (item.cache_status === "exact_hit" || item.cache_status === "semantic_hit") return <Pill tone="emerald">cache hit</Pill>
  if (item.cache_status === "bypassed") return <Pill tone="zinc">bypassed</Pill>
  return <Pill tone="amber">{item.answered_by === "model" ? "gemini" : "researched"}</Pill>
}

// ---------------------------------------------------------------- list

function UserList() {
  const router = useRouter()
  const [hours, setHours] = React.useState(720)
  const [kind, setKind] = React.useState<KindChoice>("all")
  const [searchInput, setSearchInput] = React.useState("")
  const [search, setSearch] = React.useState("")
  const loader = React.useCallback(
    () => apiUsers({ hours, search, kind: kind === "all" ? undefined : kind }),
    [hours, search, kind],
  )
  const { data, loading, error, reload, updatedAt } = usePolling<UserListPage>(loader, 60_000)
  const items = React.useMemo(() => data?.items ?? [], [data])
  const initial = loading && !data

  const totals = React.useMemo(
    () => ({
      accounts: items.filter((item) => item.kind === "account").length,
      endUsers: items.filter((item) => item.kind === "end_user").length,
      searches: items.reduce((sum, item) => sum + item.searches, 0),
      charges: items.reduce((sum, item) => sum + item.cost_inr, 0),
    }),
    [items],
  )

  return (
    <>
      <PageHeader
        title="Users"
        description="Every console account and every person using a monitored service. Open a user to see everything the gateway knows about them."
        actions={
          <>
            {updatedAt && <span className="mono-label hidden sm:inline">updated {formatRelative(updatedAt)}</span>}
            <Segmented value={hours} onChange={setHours} options={RANGE_OPTIONS} ariaLabel="Activity window" />
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
            <StatCard label="Console accounts" value={totals.accounts.toLocaleString()} hint="admins, operators, viewers, service accounts" tone="indigo" icon={<User className="h-4 w-4" />} />
            <StatCard label="Service users" value={totals.endUsers.toLocaleString()} hint="people using monitored services" tone="cyan" icon={<Users className="h-4 w-4" />} />
            <StatCard label="Searches" value={totals.searches.toLocaleString()} hint={`in the last ${rangeLabel(hours)}`} tone="emerald" icon={<MessageSquare className="h-4 w-4" />} />
            <StatCard label="Charges" value={inr(totals.charges)} hint={`in the last ${rangeLabel(hours)}`} tone="amber" icon={<Wallet className="h-4 w-4" />} />
          </>
        )}
      </div>

      <Panel
        className="mt-4"
        title="All users"
        description={data ? `${data.total.toLocaleString()} users, most recently active first. Activity totals cover the last ${rangeLabel(hours)}.` : "Loading users"}
        icon={<Users className="h-4 w-4" />}
        actions={
          <form
            onSubmit={(event) => {
              event.preventDefault()
              setSearch(searchInput.trim())
            }}
            className="flex flex-wrap items-center gap-2"
          >
            <Segmented value={kind} onChange={setKind} options={KIND_OPTIONS} ariaLabel="User type" />
            <Input
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              placeholder="Name, email, role or esone:7"
              className="h-8 w-52 text-[13px]"
              aria-label="Search users"
            />
            <Button type="submit" variant="subtle" size="sm" className="gap-1.5">
              <Search className="h-3.5 w-3.5" />
              Search
            </Button>
          </form>
        }
        flush
      >
        {initial ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 6 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : items.length === 0 ? (
          <EmptyState compact title="No users match" body={search ? `Nothing matches "${search}".` : undefined} />
        ) : (
          <Table minWidth={960}>
            <THead>
              <tr>
                <TH>User</TH>
                <TH>Type</TH>
                <TH>Last seen</TH>
                <TH align="right">API requests</TH>
                <TH align="right">Searches</TH>
                <TH align="right">Cache hits</TH>
                <TH align="right">Tokens</TH>
                <TH align="right">Charges</TH>
              </tr>
            </THead>
            <TBody>
              {items.map((item: UserListItem) => (
                <TR
                  key={item.key}
                  className="cursor-pointer hover:bg-frost"
                  onClick={() => router.push(`/dashboard/users?user=${encodeURIComponent(item.key)}`)}
                >
                  <TD>
                    <span className="block text-ink">{displayName(item)}</span>
                    <span className="block text-[11px] text-faint">
                      {item.email ?? "no email"} · <span className="font-mono">{item.key}</span>
                    </span>
                  </TD>
                  <TD>
                    <span className="flex items-center gap-1.5">
                      <KindPill kind={item.kind} role={item.role} service={item.service} />
                      {item.is_active === false && <Pill tone="zinc">inactive</Pill>}
                    </span>
                  </TD>
                  <TD className="whitespace-nowrap text-[12px] text-graphite">
                    {item.last_seen_at ? formatRelative(item.last_seen_at) : "never"}
                  </TD>
                  <TD mono align="right">{item.api_requests.toLocaleString()}</TD>
                  <TD mono align="right">{item.searches.toLocaleString()}</TD>
                  <TD mono align="right">{item.cache_hits.toLocaleString()}</TD>
                  <TD mono align="right">{item.total_tokens.toLocaleString()}</TD>
                  <TD mono align="right">{inr(item.cost_inr)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Panel>
    </>
  )
}

// -------------------------------------------------------------- detail

function UserDetailView({ userKey }: { userKey: string }) {
  const [hours, setHours] = React.useState(720)
  const loader = React.useCallback(() => apiUserDetail(userKey, hours), [userKey, hours])
  const { data, loading, error, reload, updatedAt } = usePolling<UserDetail>(loader, 60_000)
  const initial = loading && !data
  const profile = data?.profile
  const traffic = data?.traffic
  const answers = data?.answers
  const bucketShare = data?.rate_limit && data.rate_limit.limit > 0 ? (data.rate_limit.used / data.rate_limit.limit) * 100 : 0
  const viewAs = useViewAs()
  const router = useRouter()
  const viewingThisUser = viewAs.user?.key === userKey

  return (
    <>
      <Link
        href="/dashboard/users"
        className="mb-4 inline-flex items-center gap-1.5 text-[13px] text-graphite underline-offset-4 hover:text-ink hover:underline"
      >
        <ArrowLeft className="h-3.5 w-3.5" />
        All users
      </Link>
      <PageHeader
        title={profile ? displayName(profile) : userKey}
        description={profile ? `${profile.email ?? "No email on record"} · ${profile.key}` : "Loading user"}
        actions={
          <>
            {updatedAt && <span className="mono-label hidden sm:inline">updated {formatRelative(updatedAt)}</span>}
            <Segmented value={hours} onChange={setHours} options={RANGE_OPTIONS} ariaLabel="Time range" />
            <Button variant="outline" size="sm" onClick={reload} disabled={loading} className="gap-2">
              <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
              Refresh
            </Button>
            {profile && viewAs.available && !viewingThisUser && (
              <Button
                size="sm"
                className="gap-2"
                onClick={() => {
                  viewAs.setUser({
                    key: profile.key,
                    label: displayName(profile),
                    kind: profile.kind,
                    service: profile.service,
                  })
                  router.push("/dashboard")
                }}
              >
                <LayoutDashboard className="h-3.5 w-3.5" />
                View dashboard as this user
              </Button>
            )}
          </>
        }
      />

      {error && (
        <Alert variant="destructive" className="mb-6">
          {error}
        </Alert>
      )}
      {data?.notes.map((note) => (
        <Alert key={note} className="mb-4">
          {note}
        </Alert>
      ))}

      <div className="housing housing-row grid sm:grid-cols-2 lg:grid-cols-5">
        {initial || !data ? (
          Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} className="h-[120px]" />)
        ) : (
          <>
            <StatCard
              label="API requests"
              value={traffic ? traffic.total_requests.toLocaleString() : "—"}
              hint={traffic ? `${formatPercent(traffic.error_rate)} errors, ${traffic.rate_limited_requests} rate limited` : "not tracked per person"}
              tone="indigo"
              icon={<Activity className="h-4 w-4" />}
            />
            <StatCard
              label="p95 latency"
              value={traffic ? formatMs(traffic.overall_p95_response_time_ms, 0) : "—"}
              hint={traffic ? `p50 ${formatMs(traffic.overall_p50_response_time_ms, 0)}, p99 ${formatMs(traffic.overall_p99_response_time_ms, 0)}` : "not tracked per person"}
              tone="cyan"
              icon={<Gauge className="h-4 w-4" />}
            />
            <StatCard
              label="Searches"
              value={(answers?.questions ?? 0).toLocaleString()}
              hint={`${formatPercent(answers?.cache_hit_rate ?? 0)} from the cache`}
              tone="emerald"
              icon={<MessageSquare className="h-4 w-4" />}
            />
            <StatCard
              label="Tokens"
              value={((answers?.total_tokens ?? 0) + (answers?.embedding_tokens ?? 0)).toLocaleString()}
              hint={`${(answers?.total_tokens ?? 0).toLocaleString()} model, ${(answers?.embedding_tokens ?? 0).toLocaleString()} embedding`}
              tone="indigo"
              icon={<Coins className="h-4 w-4" />}
            />
            <StatCard
              label="Charges"
              value={inr(data.billing.cost_inr)}
              hint={`${data.billing.billable_tokens.toLocaleString()} tokens at ${inr(data.billing.rate_per_token)}`}
              tone="amber"
              icon={<Wallet className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1fr_1.4fr]">
        <Panel title="Profile" description={profile?.kind === "end_user" ? `Reported by ${profile.service ?? "the service"} with this person's requests and questions` : "Console account"} icon={<User className="h-4 w-4" />}>
          {initial || !profile ? (
            <Skeleton className="h-40 w-full" />
          ) : (
            <dl className="space-y-2 text-sm">
              {[
                ["Name", profile.username ?? "not provided"],
                ["Email", profile.email ?? "not provided"],
                ["Type", profile.kind === "account" ? `${profile.role ?? "account"} account` : `${profile.service ?? "service"} user`],
                ["Reference", profile.key],
                ["Status", profile.is_active === null ? "n/a" : profile.is_active ? "active" : "inactive"],
                ["Joined", profile.created_at ? formatDateTime(profile.created_at) : "unknown"],
                ["Last seen", profile.last_seen_at ? `${formatDateTime(profile.last_seen_at)} (${formatRelative(profile.last_seen_at)})` : "never"],
              ].map(([label, value]) => (
                <div key={label} className="flex items-baseline justify-between gap-4 border-b border-rule pb-2 last:border-0">
                  <dt className="text-[12px] text-graphite">{label}</dt>
                  <dd className="text-right text-ink">{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </Panel>

        <Panel
          title="API traffic"
          description={traffic ? `Average latency per bucket, last ${rangeLabel(hours)}` : "Recorded under the service's account"}
          icon={<Activity className="h-4 w-4" />}
        >
          {initial ? (
            <Skeleton className="h-[240px] w-full" />
          ) : traffic ? (
            <LatencyChart data={traffic.latency_series} />
          ) : (
            <EmptyState compact title="Not tracked per person" body="This person's requests reach the gateway through their service's account." />
          )}
        </Panel>
      </div>

      {traffic && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <Panel title="Top endpoints" description="By request count" flush>
            {traffic.top_endpoints.length === 0 ? (
              <EmptyState compact title="No requests in this window" />
            ) : (
              <Table minWidth={420}>
                <THead>
                  <tr>
                    <TH>Endpoint</TH>
                    <TH align="right">Requests</TH>
                    <TH align="right">Avg</TH>
                    <TH align="right">Errors</TH>
                  </tr>
                </THead>
                <TBody>
                  {traffic.top_endpoints.slice(0, 8).map((row) => (
                    <TR key={row.endpoint}>
                      <TD mono className="max-w-[260px] truncate text-ink">{row.endpoint}</TD>
                      <TD mono align="right">{row.count}</TD>
                      <TD mono align="right">{formatMs(row.avg_time, 0)}</TD>
                      <TD mono align="right">{row.errors}</TD>
                    </TR>
                  ))}
                </TBody>
              </Table>
            )}
          </Panel>
          <Panel title="Recent requests" description="Newest first" flush>
            {traffic.recent_requests.length === 0 ? (
              <EmptyState compact title="No requests in this window" />
            ) : (
              <ul className="divide-y divide-rule">
                {traffic.recent_requests.slice(0, 8).map((request, index) => (
                  <li key={`${request.created_at}-${index}`} className="flex items-center justify-between gap-3 px-5 py-2.5">
                    <span className="flex min-w-0 items-center gap-2">
                      <MethodPill method={request.method} />
                      <span className="truncate font-mono text-[12px] text-ink">{request.endpoint}</span>
                    </span>
                    <span className="flex shrink-0 items-center gap-1.5">
                      {request.cache_hit && <Pill tone="emerald">hit</Pill>}
                      <StatusCodePill status={request.status_code} />
                      <span className="w-14 text-right font-mono text-[11px] text-graphite">{formatMs(request.response_time_ms, 0)}</span>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      )}

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel
          title="Searches and answers"
          description={answers ? `${answers.questions} in the last ${rangeLabel(hours)}: ${answers.cache_hits} from the cache, ${answers.crawled} generated, ${answers.errors + answers.blocked} failed or blocked` : "Questions this user asked"}
          icon={<MessageSquare className="h-4 w-4" />}
          flush
        >
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 4 }).map((_, index) => (
                <Skeleton key={index} className="h-12 w-full" />
              ))}
            </div>
          ) : (data?.recent_answers.length ?? 0) === 0 ? (
            <EmptyState compact title="No searches in this window" />
          ) : (
            <ul className="divide-y divide-rule">
              {data?.recent_answers.map((item) => (
                <li key={item.id} className="px-5 py-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-[13px] text-ink">{item.question}</p>
                      <p className="mt-0.5 text-[11px] text-faint">
                        {formatDateTime(item.created_at)} · {formatMs(item.latency_ms, 0)}
                        {item.total_tokens > 0 ? ` · ${item.total_tokens} tokens` : ""}
                        {item.cost_inr > 0 ? ` · ${inr(item.cost_inr)}` : ""}
                      </p>
                    </div>
                    <AnswerStatusPill item={item} />
                  </div>
                  {item.answer && <p className="mt-1.5 line-clamp-2 text-[12px] leading-relaxed text-graphite">{item.answer}</p>}
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <div className="space-y-4">
          <Panel title="Billing" description="Charged per token for answers not served from the cache" icon={<Wallet className="h-4 w-4" />}>
            {initial || !data ? (
              <Skeleton className="h-28 w-full" />
            ) : (
              <dl className="space-y-2 text-sm">
                {[
                  ["Rate", `${inr(data.billing.rate_per_token)} per token`],
                  ["Billable tokens", data.billing.billable_tokens.toLocaleString()],
                  ["Paid answers", data.billing.paid_answers.toLocaleString()],
                  ["Free answers (cache)", data.billing.free_answers.toLocaleString()],
                  ["Total", inr(data.billing.cost_inr)],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-baseline justify-between gap-4 border-b border-rule pb-2 last:border-0">
                    <dt className="text-[12px] text-graphite">{label}</dt>
                    <dd className="font-mono text-ink">{value}</dd>
                  </div>
                ))}
              </dl>
            )}
          </Panel>

          {data?.rate_limit && (
            <Panel title="Rate limit" description={`${data.rate_limit.tier} tier, ${data.rate_limit.identifier}`} icon={<Timer className="h-4 w-4" />}>
              <div className="flex items-end justify-between">
                <p className="font-mono text-3xl tracking-tight text-ink">{data.rate_limit.remaining}</p>
                <p className="text-xs text-faint">left of {data.rate_limit.limit}</p>
              </div>
              <div className="mt-3 h-2.5 w-full overflow-hidden rounded bg-frost" role="img" aria-label="Bucket usage">
                <div className={cn("h-full rounded", bucketShare > 80 ? "bg-warn/40" : "bg-steel/30")} style={{ width: `${Math.min(100, bucketShare)}%` }} />
              </div>
              <p className="mt-2 text-[11px] text-faint">
                {data.rate_limit.has_bucket ? `Full again in ${data.rate_limit.reset_in_seconds}s` : "No requests yet in this period"}
              </p>
            </Panel>
          )}
        </div>
      </div>

      {(data?.ai_usage || data?.guardrails) && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {data?.ai_usage && (
            <Panel
              title="AI usage"
              description={`${data.ai_usage.requests} model calls, ${data.ai_usage.total_tokens.toLocaleString()} tokens, ~$${data.ai_usage.estimated_cost_usd.toFixed(4)} provider cost (estimate)`}
              icon={<Bot className="h-4 w-4" />}
              flush
            >
              {data.ai_calls.length === 0 ? (
                <EmptyState compact title="No model calls in this window" />
              ) : (
                <Table minWidth={520}>
                  <THead>
                    <tr>
                      <TH>Time</TH>
                      <TH>Feature</TH>
                      <TH>Model</TH>
                      <TH align="right">Tokens</TH>
                      <TH align="right">Latency</TH>
                    </tr>
                  </THead>
                  <TBody>
                    {data.ai_calls.map((call) => (
                      <TR key={call.id}>
                        <TD className="whitespace-nowrap text-[12px] text-graphite">{formatDateTime(call.created_at)}</TD>
                        <TD>{call.feature}</TD>
                        <TD mono className="text-[12px]">{call.served_model ?? call.requested_model ?? "—"}</TD>
                        <TD mono align="right">{call.total_tokens}</TD>
                        <TD mono align="right">{formatMs(call.latency_ms, 0)}</TD>
                      </TR>
                    ))}
                  </TBody>
                </Table>
              )}
            </Panel>
          )}
          {data?.guardrails && (
            <Panel
              title="Guardrail events"
              description={`${data.guardrails.total_events} events, ${data.guardrails.blocked_requests} blocked, ${data.guardrails.high_severity} high severity`}
              icon={<ShieldAlert className="h-4 w-4" />}
              flush
            >
              {data.guardrail_events.length === 0 ? (
                <EmptyState compact title="Nothing flagged in this window" />
              ) : (
                <ul className="divide-y divide-rule">
                  {data.guardrail_events.map((event) => (
                    <li key={event.id} className="flex items-start justify-between gap-3 px-5 py-2.5">
                      <div className="min-w-0">
                        <p className="text-[13px] text-ink">{event.category.replace(/_/g, " ")}</p>
                        <p className="mt-0.5 truncate text-[11px] text-faint">
                          {formatDateTime(event.created_at)} · {event.feature} · {event.detail}
                        </p>
                      </div>
                      <span className="flex shrink-0 gap-1.5">
                        <Pill tone={event.severity === "high" ? "red" : event.severity === "medium" ? "amber" : "zinc"}>{event.severity}</Pill>
                        {event.blocked && <Pill tone="red">blocked</Pill>}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          )}
        </div>
      )}
    </>
  )
}

// ---------------------------------------------------------------- page

function UsersPageInner() {
  const auth = useAuth()
  const params = useSearchParams()
  const userKey = params.get("user")

  if (auth.ready && !auth.isAdmin) {
    return (
      <EmptyState
        icon={<ShieldAlert className="h-5 w-5" />}
        title="Admins only"
        body="The user directory shows every user's data, so only administrators can open it."
      />
    )
  }
  return userKey ? <UserDetailView userKey={userKey} /> : <UserList />
}

export default function UsersPage() {
  return (
    <React.Suspense fallback={<Skeleton className="h-[400px] w-full" />}>
      <UsersPageInner />
    </React.Suspense>
  )
}
