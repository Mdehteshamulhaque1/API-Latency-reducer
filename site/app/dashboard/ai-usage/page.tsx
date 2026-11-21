"use client"

import * as React from "react"
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts"
import { Coins, Cpu, RefreshCw, Timer, TriangleAlert } from "lucide-react"

import { AXIS_TICK, CHART, TOOLTIP_ITEM_STYLE, TOOLTIP_LABEL_STYLE, TOOLTIP_STYLE } from "@/components/charts/chart-theme"
import { Alert } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { EmptyState } from "@/components/ui/empty-state"
import { PageHeader } from "@/components/ui/page-header"
import { Panel } from "@/components/ui/panel"
import { Pill, type PillTone } from "@/components/ui/pill"
import { RANGE_OPTIONS, Segmented, rangeLabel } from "@/components/ui/segmented"
import { Skeleton } from "@/components/ui/skeleton"
import { StatCard } from "@/components/ui/stat-card"
import { Table, TBody, TD, TH, THead, TR } from "@/components/ui/table"
import { apiAiUsageRequests, apiAiUsageSummary, type AIRequestLogItem, type AIUsageSummary } from "@/lib/api"
import { usePolling } from "@/lib/use-auth"
import { useMonitoredService } from "@/lib/use-service"
import { cn, formatDateTime, formatMs, formatPercent, formatRelative, parseUtc } from "@/lib/utils"

const OUTCOME_TONE: Record<AIRequestLogItem["outcome"], PillTone> = {
  success: "indigo",
  cache_hit: "emerald",
  error: "red",
}

interface UsageData {
  summary: AIUsageSummary
  requests: AIRequestLogItem[]
}

function TokensChart({ summary }: { summary: AIUsageSummary }) {
  const series = summary.series.map((point) => {
    const date = parseUtc(point.timestamp)
    return {
      label: Number.isNaN(date.getTime()) ? point.timestamp : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      tokens: point.total_tokens,
      requests: point.requests,
      errors: point.errors,
    }
  })
  if (series.length === 0) {
    return (
      <div className="flex h-[240px] items-center justify-center rounded border border-dashed border-rule text-sm text-faint">
        No LLM calls in this window
      </div>
    )
  }
  return (
    <ResponsiveContainer width="100%" height={240}>
      <BarChart data={series} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} barCategoryGap="30%">
        <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} minTickGap={24} />
        <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} allowDecimals={false} width={56} />
        <Tooltip cursor={{ fill: "rgba(255,255,255,0.04)" }} contentStyle={TOOLTIP_STYLE} labelStyle={TOOLTIP_LABEL_STYLE} itemStyle={TOOLTIP_ITEM_STYLE} />
        <Legend verticalAlign="top" align="right" iconType="square" iconSize={10} wrapperStyle={{ fontSize: 11, color: "#9BA1B0", paddingBottom: 8 }} />
        <Bar dataKey="tokens" name="Tokens" fill={CHART.avg} stroke={CHART.surface} strokeWidth={1} radius={[4, 4, 0, 0]} isAnimationActive={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export default function AiUsagePage() {
  const [hours, setHours] = React.useState(24)
  const monitored = useMonitoredService()
  const service = monitored.service ?? undefined
  const loader = React.useCallback(async (): Promise<UsageData> => {
    const [summary, requests] = await Promise.all([
      apiAiUsageSummary(hours, { service }),
      apiAiUsageRequests(hours, 50, { service }),
    ])
    return { summary, requests: requests.items }
  }, [hours, service])
  const { data, loading, error, reload, updatedAt } = usePolling<UsageData>(loader, monitored.loading ? null : 30_000)

  const summary = data?.summary
  const requests = React.useMemo(() => data?.requests ?? [], [data])
  const initial = loading && !data

  return (
    <>
      <PageHeader
        eyebrow="ai usage"
        title={monitored.monitoring ? `${monitored.label} tokens and cost` : "Tokens and cost"}
        description={
          monitored.monitoring
            ? `Every LLM call made on ${monitored.label}'s behalf (its questions that needed a model): tokens as reported by the provider, latency, outcome, and an estimated cost.`
            : "Every LLM call made through the gateway: tokens as reported by the provider, latency, outcome, and an estimated cost from the configured pricing table."
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

      <div className="housing housing-row grid sm:grid-cols-2 lg:grid-cols-4">
        {initial ? (
          Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-[120px]" />)
        ) : (
          <>
            <StatCard label="LLM requests" value={(summary?.requests ?? 0).toLocaleString()} hint={`${summary?.cache_hits ?? 0} cache hits, ${summary?.fallbacks ?? 0} fallbacks, ${summary?.scope === "all" ? "all users" : summary?.scope === "service" ? `${monitored.label}'s calls` : "your calls"}`} tone="indigo" icon={<Cpu className="h-4 w-4" />} />
            <StatCard label="Tokens" value={(summary?.total_tokens ?? 0).toLocaleString()} hint={`${(summary?.prompt_tokens ?? 0).toLocaleString()} prompt, ${(summary?.completion_tokens ?? 0).toLocaleString()} completion`} tone="cyan" icon={<Coins className="h-4 w-4" />} />
            <StatCard label="Estimated cost" value={`$${(summary?.estimated_cost_usd ?? 0).toFixed(4)}`} hint="estimate from PRICING_TABLE, not a bill" tone="indigo" icon={<Coins className="h-4 w-4" />} />
            <StatCard label="Avg latency" value={formatMs(summary?.avg_latency_ms ?? 0)} hint={`${formatPercent(summary?.error_rate ?? 0)} errors`} tone={(summary?.error_rate ?? 0) > 5 ? "amber" : "emerald"} icon={<Timer className="h-4 w-4" />} />
          </>
        )}
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-[1.4fr_1fr]">
        <Panel title="Tokens over time" description={`per bucket, last ${rangeLabel(hours)}`} actions={updatedAt ? <span className="mono-label">updated {formatRelative(updatedAt)}</span> : undefined}>
          {initial || !summary ? <Skeleton className="h-[240px] w-full" /> : <TokensChart summary={summary} />}
        </Panel>

        <Panel title="By model" description="Served model as reported by the provider" flush>
          {initial ? (
            <div className="space-y-3 p-5">
              {Array.from({ length: 3 }).map((_, index) => (
                <Skeleton key={index} className="h-10 w-full" />
              ))}
            </div>
          ) : !summary || summary.by_model.length === 0 ? (
            <EmptyState compact title="No calls yet" body="Use the assistant or send requests to POST /api/v1/chat to generate traffic." />
          ) : (
            <ul className="divide-y divide-rule">
              {summary.by_model.map((model) => (
                <li key={model.served_model} className="px-5 py-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-mono text-[13px] text-ink">{model.served_model}</p>
                    <span className="font-mono text-xs text-graphite">{model.requests} req</span>
                  </div>
                  <p className="mt-1 text-[11px] text-faint">
                    {model.total_tokens.toLocaleString()} tokens, {formatMs(model.avg_latency_ms)} avg, ~${model.estimated_cost_usd.toFixed(4)}, {model.cache_hits} hits, {model.errors} errors
                  </p>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </div>

      <Panel className="mt-4" title="Recent calls" description="No prompt or completion text is stored" icon={<TriangleAlert className="h-4 w-4" />} flush>
        {initial ? (
          <div className="space-y-3 p-5">
            {Array.from({ length: 5 }).map((_, index) => (
              <Skeleton key={index} className="h-10 w-full" />
            ))}
          </div>
        ) : requests.length === 0 ? (
          <EmptyState compact title="No calls in this window" />
        ) : (
          <Table minWidth={820}>
            <THead>
              <tr>
                <TH>Time</TH>
                <TH>Feature</TH>
                <TH>Model</TH>
                <TH>Outcome</TH>
                <TH align="right">Tokens</TH>
                <TH align="right">Latency</TH>
                <TH align="right">Est. cost</TH>
                <TH>Correlation ID</TH>
              </tr>
            </THead>
            <TBody>
              {requests.map((item) => (
                <TR key={item.id}>
                  <TD className="whitespace-nowrap text-xs text-faint">{formatDateTime(item.created_at)}</TD>
                  <TD mono className="text-graphite">{item.feature}</TD>
                  <TD mono className="text-ink">{item.served_model ?? item.requested_model ?? "—"}</TD>
                  <TD>
                    <div className="flex items-center gap-1.5">
                      <Pill tone={OUTCOME_TONE[item.outcome]}>{item.outcome.replace("_", " ")}</Pill>
                      {item.fallback_used && <Pill tone="indigo">fallback</Pill>}
                      {item.error_code && <span className="font-mono text-[10px] text-signal">{item.error_code}</span>}
                    </div>
                  </TD>
                  <TD mono align="right">{item.total_tokens.toLocaleString()}</TD>
                  <TD mono align="right">{formatMs(item.latency_ms)}</TD>
                  <TD mono align="right">{item.estimated_cost_usd > 0 ? `$${item.estimated_cost_usd.toFixed(5)}` : "—"}</TD>
                  <TD mono className="max-w-[160px] truncate text-faint" title={item.correlation_id ?? ""}>{item.correlation_id ?? "—"}</TD>
                </TR>
              ))}
            </TBody>
          </Table>
        )}
      </Panel>
    </>
  )
}
