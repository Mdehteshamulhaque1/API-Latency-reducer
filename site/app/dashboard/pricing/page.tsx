"use client"

import * as React from "react"
import { CalendarDays, Coins, Cpu, Info, Receipt, RefreshCw, Users, Wallet } from "lucide-react"

import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table"
import {
  apiPricing,
  apiPricingUsers,
  type PricingTable,
  type UserTokenUsage,
  type UserTokenUsageResponse,
} from "@/lib/api"
import { useAuth, usePolling } from "@/lib/use-auth"
import { cn, formatRelative } from "@/lib/utils"

function formatRate(value: number): string {
  if (!Number.isFinite(value)) return "—"
  if (value === 0) return "Free"
  return `$${value.toFixed(value < 0.01 ? 4 : 2)}`
}

function formatInr(value: number): string {
  if (!Number.isFinite(value)) return "—"
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value)
}

function userLabel(item: UserTokenUsage): string {
  if (item.user_id === null) return item.end_user ?? "Unattributed"
  return item.username ?? `user ${item.user_id}`
}

function AdminTokenUsage({ isAdmin }: { isAdmin: boolean }) {
  const loader = React.useCallback(() => apiPricingUsers(), [])
  const { data, loading, error, reload, updatedAt } = usePolling<UserTokenUsageResponse>(loader, 60_000)
  const initial = loading && !data

  return (
    <Panel
      className="mt-4"
      title={isAdmin ? "Per-user token billing" : "Your token billing"}
      description={data ? `${formatInr(data.rate_per_token)} ${data.unit}` : "Non-cached answer tokens by caller"}
      icon={<Users className="h-4 w-4" />}
      flush
      actions={
        <>
          {updatedAt && <span className="mono-label hidden sm:inline">updated {formatRelative(updatedAt)}</span>}
          <Button variant="outline" size="sm" onClick={reload} disabled={loading} className="gap-2">
            <RefreshCw className={cn("h-3.5 w-3.5", loading && "animate-spin")} />
            Refresh
          </Button>
        </>
      }
    >
      {error && (
        <Alert variant="destructive" className="m-5">
          {error}
        </Alert>
      )}
      {initial ? (
        <div className="grid gap-4 p-5 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => <Skeleton key={index} className="h-[100px]" />)}
        </div>
      ) : !data ? (
        <div className="p-5"><EmptyState compact title="No token billing data" /></div>
      ) : (
        <>
          <div className="housing housing-row grid sm:grid-cols-3">
            <StatCard
              label="Charge rate"
              value={formatInr(data.rate_per_token)}
              hint={data.unit}
              tone="amber"
              icon={<Receipt className="h-4 w-4" />}
            />
            <StatCard
              label="Billable tokens"
              value={data.total_billable_tokens.toLocaleString()}
              hint="non-cached answer tokens"
              tone="indigo"
              icon={<Coins className="h-4 w-4" />}
            />
            <StatCard
              label="Total charge"
              value={formatInr(data.total_cost_inr)}
              hint="INR, based on recorded usage"
              tone="emerald"
              icon={<Wallet className="h-4 w-4" />}
            />
          </div>
          <p className="px-5 pt-4 text-[12px] text-faint">{data.note}</p>
          {data.items.length === 0 ? (
            <div className="p-5"><EmptyState compact title="No users yet" /></div>
          ) : (
            <Table minWidth={720}>
              <THead>
                <tr>
                  <TH>User</TH>
                  <TH>End user</TH>
                  <TH align="right">Answers</TH>
                  <TH align="right">Cached</TH>
                  <TH align="right">Uncached</TH>
                  <TH align="right">Tokens</TH>
                  <TH align="right">Charge</TH>
                </tr>
              </THead>
              <TBody>
                {data.items.map((item) => (
                  <TR key={`${item.user_id ?? "anonymous"}:${item.end_user ?? "none"}`}>
                    <TD>
                      <span className="text-ink">{userLabel(item)}</span>
                      {item.email && <span className="block text-[11px] text-faint">{item.email}</span>}
                    </TD>
                    <TD mono>{item.end_user ?? "—"}</TD>
                    <TD mono align="right">{item.answers.toLocaleString()}</TD>
                    <TD mono align="right">{item.cached_answers.toLocaleString()}</TD>
                    <TD mono align="right">{item.uncached_answers.toLocaleString()}</TD>
                    <TD mono align="right">{item.billable_tokens.toLocaleString()}</TD>
                    <TD mono align="right">{formatInr(item.cost_inr)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </>
      )}
    </Panel>
  )
}

export default function PricingPage() {
  const auth = useAuth()
  const loader = React.useCallback(() => apiPricing(), [])
  const { data, loading, error, reload, updatedAt } = usePolling<PricingTable>(loader, null)
  const pricing = data
  const initial = loading && !data

  return (
    <>
      <PageHeader
        eyebrow="pricing"
        title="Pricing tables"
        description="The rates used to estimate LLM and embedding costs across the gateway. These are estimates, not provider billing."
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

      <div className="housing housing-row grid sm:grid-cols-2 lg:grid-cols-5">
        {initial ? (
          Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} className="h-[120px]" />)
        ) : (
          <>
            <StatCard
              label="Currency"
              value={pricing?.currency ?? "—"}
              hint="configured via PRICING_CURRENCY"
              tone="indigo"
              icon={<Wallet className="h-4 w-4" />}
            />
            <StatCard
              label="Effective date"
              value={pricing?.effective_date ?? "—"}
              hint="when these rates were last checked"
              tone="cyan"
              icon={<CalendarDays className="h-4 w-4" />}
            />
            <StatCard
              label="Chat models"
              value={(pricing?.chat_models.length ?? 0).toLocaleString()}
              hint="prompt and completion rates"
              tone="indigo"
              icon={<Cpu className="h-4 w-4" />}
            />
            <StatCard
              label="Embedding models"
              value={(pricing?.embedding_models.length ?? 0).toLocaleString()}
              hint="per-token embedding rates"
              tone="emerald"
              icon={<Coins className="h-4 w-4" />}
            />
            <StatCard
              label="Answer tokens"
              value={pricing?.billing ? formatInr(pricing.billing.rate_per_token) : "—"}
              hint="per non-cached token"
              tone="amber"
              icon={<Receipt className="h-4 w-4" />}
            />
          </>
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel
          title="Chat models"
          description={pricing ? `Prompt and completion rates ${pricing.unit}` : "Prompt and completion rates"}
          icon={<Cpu className="h-4 w-4" />}
          flush
        >
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 5 }).map((_, index) => (
                <Skeleton key={index} className="h-9 w-full" />
              ))}
            </div>
          ) : !pricing || pricing.chat_models.length === 0 ? (
            <EmptyState compact title="No chat pricing configured" />
          ) : (
            <Table minWidth={520}>
              <THead>
                <tr>
                  <TH>Model</TH>
                  <TH align="right">Prompt</TH>
                  <TH align="right">Completion</TH>
                </tr>
              </THead>
              <TBody>
                {pricing.chat_models.map((model) => (
                  <TR key={model.model}>
                    <TD mono className="text-ink">{model.model}</TD>
                    <TD mono align="right">{formatRate(model.prompt_per_million)}</TD>
                    <TD mono align="right">{formatRate(model.completion_per_million)}</TD>
                  </TR>
                ))}
              </TBody>
            </Table>
          )}
        </Panel>

        <div className="grid gap-4">
          <Panel title="Fallback pricing" description="Used when a model is not listed in a table" flush>
            {initial ? (
              <div className="space-y-3 p-5">
                {Array.from({ length: 3 }).map((_, index) => (
                  <Skeleton key={index} className="h-9 w-full" />
                ))}
              </div>
            ) : !pricing ? (
              <EmptyState compact title="No fallback pricing" />
            ) : (
              <ul className="divide-y divide-rule">
                <li className="flex items-center justify-between gap-3 px-5 py-3">
                  <span className="text-[13px] text-graphite">Chat prompt</span>
                  <span className="font-mono text-xs text-ink">{formatRate(pricing.defaults.chat_prompt_per_million)}</span>
                </li>
                <li className="flex items-center justify-between gap-3 px-5 py-3">
                  <span className="text-[13px] text-graphite">Chat completion</span>
                  <span className="font-mono text-xs text-ink">{formatRate(pricing.defaults.chat_completion_per_million)}</span>
                </li>
                <li className="flex items-center justify-between gap-3 px-5 py-3">
                  <span className="text-[13px] text-graphite">Embeddings</span>
                  <span className="font-mono text-xs text-ink">{formatRate(pricing.defaults.embedding_per_million)}</span>
                </li>
              </ul>
            )}
          </Panel>

          <Panel title="How estimates work" description={pricing?.source ?? "Configured pricing tables"} icon={<Info className="h-4 w-4" />}>
            {initial ? (
              <Skeleton className="h-16 w-full" />
            ) : !pricing ? (
              <EmptyState compact title="No pricing details" />
            ) : (
              <div className="space-y-2 text-[13px] text-graphite">
                <p>
                  Rates are expressed {pricing.unit}. A request is estimated as prompt tokens and completion tokens
                  multiplied by the matching model rate.
                </p>
                <p className="text-faint">{pricing.note}</p>
              </div>
            )}
          </Panel>
        </div>
      </div>

      {auth.ready && <AdminTokenUsage isAdmin={auth.isAdmin} />}

      <Panel className="mt-4" title="Embedding models" description={pricing ? `Token rates ${pricing.unit}` : "Token rates"} icon={<Coins className="h-4 w-4" />} flush>
        {initial ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 4 }).map((_, index) => (
              <Skeleton key={index} className="h-9 w-full" />
            ))}
          </div>
        ) : !pricing || pricing.embedding_models.length === 0 ? (
          <EmptyState compact title="No embedding pricing configured" />
        ) : (
          <Table minWidth={520}>
            <THead>
              <tr>
                <TH>Model</TH>
                <TH align="right">Price</TH>
              </tr>
            </THead>
            <TBody>
              {pricing.embedding_models.map((model) => (
                <TR key={model.model}>
                  <TD mono className="text-ink">{model.model}</TD>
                  <TD mono align="right">{formatRate(model.price_per_million)}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Panel>
    </>
  )
}
