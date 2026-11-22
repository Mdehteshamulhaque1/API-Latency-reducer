"use client"

import * as React from "react"
import { ChevronDown, Coins, MessageSquare, Search, Sparkles } from "lucide-react"

import { Skeleton } from "@/components/ui/skeleton"
import { apiQueryBreakdown, type QueryBreakdown, type QueryCategory } from "@/lib/api"
import { usePolling } from "@/lib/use-auth"
import { cn, formatMs } from "@/lib/utils"

const GROUP_LABEL: Record<QueryCategory["group"], string> = {
  query: "Real queries",
  supporting: "Supporting requests",
  outbound: "Calls made for users",
}

const GROUP_HINT: Record<QueryCategory["group"], string> = {
  query: "Questions users actually asked",
  supporting: "Sign-in, history, page loads and health checks",
  outbound: "AI model and gateway calls made to answer users",
}

function inr(value: number): string {
  return `₹${value.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function Tile({
  icon,
  label,
  value,
  hint,
}: {
  icon: React.ReactNode
  label: string
  value: string
  hint: string
}) {
  return (
    <div className="border-b border-relay/20 p-4 sm:border-b-0 sm:border-r last:border-r-0">
      <p className="flex items-center gap-1.5 text-[12px] text-graphite">
        <span className="text-relay">{icon}</span>
        {label}
      </p>
      <p className="mt-1.5 font-mono text-[26px] leading-none text-ink">{value}</p>
      <p className="mt-1.5 text-[12px] text-graphite">{hint}</p>
    </div>
  )
}

function CategoryRow({ category, highlight }: { category: QueryCategory; highlight: boolean }) {
  const [open, setOpen] = React.useState(false)
  const canOpen = category.endpoints.length > 0
  return (
    <>
      <tr className={cn("border-t border-rule", highlight && "bg-relay/5")}>
        <td className="px-4 py-2.5">
          <button
            type="button"
            onClick={() => canOpen && setOpen((v) => !v)}
            disabled={!canOpen}
            aria-expanded={open}
            className="flex items-center gap-1.5 text-left text-sm text-ink disabled:cursor-default"
          >
            <ChevronDown
              className={cn("h-3.5 w-3.5 shrink-0 text-faint transition-transform", !open && "-rotate-90", !canOpen && "opacity-0")}
            />
            <span className={cn(highlight && "font-medium")}>{category.label}</span>
          </button>
          <p className="ml-5 text-[12px] text-graphite">{category.description}</p>
        </td>
        <td className={cn("px-4 py-2.5 text-right font-mono text-sm", highlight ? "text-ink" : "text-graphite")}>
          {category.requests.toLocaleString()}
        </td>
        <td className={cn("px-4 py-2.5 text-right font-mono text-sm", category.errors > 0 ? "text-signal" : "text-faint")}>
          {category.errors.toLocaleString()}
        </td>
        <td className="px-4 py-2.5 text-right font-mono text-sm text-graphite">
          {category.requests ? formatMs(category.avg_response_time_ms, 0) : "—"}
        </td>
      </tr>
      {open &&
        category.endpoints.map((item) => (
          <tr key={`${item.method} ${item.endpoint}`} className={cn(highlight && "bg-relay/5")}>
            <td className="px-4 py-1 pl-10 font-mono text-[12px] text-graphite" colSpan={1}>
              {item.method} {item.endpoint}
            </td>
            <td className="px-4 py-1 text-right font-mono text-[12px] text-graphite">{item.requests.toLocaleString()}</td>
            <td colSpan={2} />
          </tr>
        ))}
    </>
  )
}

/**
 * Highlighted "real queries" section: the questions users asked (search and
 * chatbot) and what the searches cost, separated from sign-in, history and
 * health traffic that the plain request counters also include.
 */
export function RealQueries({ service, hours = 24 }: { service: string | null; hours?: number }) {
  const loader = React.useCallback(() => apiQueryBreakdown(hours, service ?? undefined), [hours, service])
  const { data, error } = usePolling<QueryBreakdown>(loader, 30_000)

  if (error && !data) return null
  if (!data) return <Skeleton className="mb-6 h-[260px] w-full" />

  const by = (key: string) => data.categories.find((c) => c.key === key)
  const search = by("search")
  const chatbot = by("chatbot")
  const ai = by("ai_provider")
  const s = data.searches
  const groups: QueryCategory["group"][] = ["query", "supporting", "outbound"]

  return (
    <section className="mb-6 overflow-hidden rounded border-2 border-relay/40 bg-paper" aria-labelledby="real-queries-title">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-relay/20 bg-relay/5 px-5 py-3.5">
        <div>
          <h2 id="real-queries-title" className="text-sm font-medium text-ink">
            Real queries <span className="text-graphite">· last {hours} hours</span>
          </h2>
          <p className="mt-0.5 text-[12px] text-graphite">
            Questions users actually asked, and what they cost. Every other request is counted separately below.
          </p>
        </div>
        <p className="font-mono text-[12px] text-graphite">
          {data.total_requests.toLocaleString()} requests = <span className="text-ink">{data.real_queries.toLocaleString()} queries</span>
          {" + "}
          {data.supporting_requests.toLocaleString()} supporting + {data.outbound_calls.toLocaleString()} outbound
        </p>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4">
        <Tile
          icon={<Sparkles className="h-3.5 w-3.5" />}
          label="Real queries"
          value={data.real_queries.toLocaleString()}
          hint={`${(search?.requests ?? 0).toLocaleString()} search + ${(chatbot?.requests ?? 0).toLocaleString()} chatbot`}
        />
        <Tile
          icon={<Search className="h-3.5 w-3.5" />}
          label="Search answers"
          value={s.questions.toLocaleString()}
          hint={`${s.cache_hits} from cache, ${s.fresh_answers} fresh, avg ${formatMs(s.avg_latency_ms, 0)}`}
        />
        <Tile
          icon={<Coins className="h-3.5 w-3.5" />}
          label="Search charges"
          value={inr(s.cost_inr)}
          hint={`${s.billable_tokens.toLocaleString()} billable tokens at ${inr(s.rate_per_token_inr)}`}
        />
        <Tile
          icon={<MessageSquare className="h-3.5 w-3.5" />}
          label="Chatbot"
          value={(chatbot?.requests ?? 0).toLocaleString()}
          hint={`${(ai?.requests ?? 0).toLocaleString()} AI model calls, not billed`}
        />
      </div>

      <div className="overflow-x-auto border-t border-relay/20">
        <table className="w-full min-w-[560px] text-left">
          <thead>
            <tr className="text-[12px] text-graphite">
              <th className="px-4 py-2 font-normal">Request type (click to see endpoints)</th>
              <th className="px-4 py-2 text-right font-normal">Requests</th>
              <th className="px-4 py-2 text-right font-normal">Errors</th>
              <th className="px-4 py-2 text-right font-normal">Avg time</th>
            </tr>
          </thead>
          {groups.map((group) => {
            const rows = data.categories.filter((c) => c.group === group && (group === "query" || c.requests > 0))
            if (rows.length === 0) return null
            return (
              <tbody key={group}>
                <tr className="border-t border-rule bg-frost">
                  <td colSpan={4} className="px-4 py-1.5 text-[12px] text-graphite">
                    <span className={cn("font-medium", group === "query" ? "text-relay" : "text-ink")}>{GROUP_LABEL[group]}</span>
                    {" · "}
                    {GROUP_HINT[group]}
                  </td>
                </tr>
                {rows.map((category) => (
                  <CategoryRow key={category.key} category={category} highlight={group === "query"} />
                ))}
              </tbody>
            )
          })}
        </table>
      </div>
    </section>
  )
}
