"use client"

import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import type { LatencyPoint } from "@/lib/api"
import { formatMs, parseUtc } from "@/lib/utils"

import { AXIS_TICK, CHART, TOOLTIP_ITEM_STYLE, TOOLTIP_LABEL_STYLE, TOOLTIP_STYLE, msTick } from "./chart-theme"

export type { LatencyPoint }

function formatTick(value: string): string {
  const date = parseUtc(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

/** Single-series average latency over time. */
export function LatencyChart({ data, height = 240 }: { data: LatencyPoint[]; height?: number }) {
  const series = data.map((point) => ({
    label: formatTick(point.timestamp),
    latency: Math.round(point.avg_response_time_ms * 10) / 10,
    requests: point.request_count,
  }))

  if (series.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-rule-strong text-sm text-graphite"
        style={{ height }}
      >
        No latency data in this window
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={series} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
        <defs>
          <linearGradient id="latency-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={CHART.avg} stopOpacity={0.18} />
            <stop offset="100%" stopColor={CHART.avg} stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} minTickGap={24} />
        <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} tickFormatter={msTick} width={56} />
        <Tooltip
          cursor={{ stroke: CHART.cursor }}
          contentStyle={TOOLTIP_STYLE}
          labelStyle={TOOLTIP_LABEL_STYLE}
          itemStyle={TOOLTIP_ITEM_STYLE}
          formatter={(value: number, name: string) =>
            name === "Avg latency" ? [formatMs(value), name] : [value, name]
          }
        />
        <Area
          type="monotone"
          dataKey="latency"
          stroke={CHART.avg}
          strokeWidth={2}
          fill="url(#latency-fill)"
          name="Avg latency"
          activeDot={{ r: 4, strokeWidth: 2, stroke: CHART.surface }}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
