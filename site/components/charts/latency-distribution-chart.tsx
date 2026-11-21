"use client"

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import type { LatencyDistributionPoint } from "@/lib/api"
import { formatMs, parseUtc } from "@/lib/utils"

import { AXIS_TICK, CHART, TOOLTIP_ITEM_STYLE, TOOLTIP_LABEL_STYLE, TOOLTIP_STYLE, msTick } from "./chart-theme"

function formatTick(value: string): string {
  const date = parseUtc(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

const SERIES = [
  { key: "avg", name: "Avg", color: CHART.avg },
  { key: "p95", name: "p95", color: CHART.p95 },
  { key: "p99", name: "p99", color: CHART.p99 },
] as const

/** Avg / p95 / p99 latency per time bucket, one shared y-axis. */
export function LatencyDistributionChart({
  data,
  height = 260,
}: {
  data: LatencyDistributionPoint[]
  height?: number
}) {
  const series = data.map((point) => ({
    label: formatTick(point.timestamp),
    avg: Math.round(point.avg_response_time_ms * 10) / 10,
    p95: Math.round(point.p95_response_time_ms * 10) / 10,
    p99: Math.round(point.p99_response_time_ms * 10) / 10,
    requests: point.request_count,
  }))

  if (series.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-rule-strong text-sm text-graphite"
        style={{ height }}
      >
        No latency distribution in this window
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={series} margin={{ top: 8, right: 8, left: -12, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} minTickGap={24} />
        <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} tickFormatter={msTick} width={56} />
        <Tooltip
          cursor={{ stroke: CHART.cursor }}
          contentStyle={TOOLTIP_STYLE}
          labelStyle={TOOLTIP_LABEL_STYLE}
          itemStyle={TOOLTIP_ITEM_STYLE}
          formatter={(value: number, name: string) => [formatMs(value), name]}
        />
        <Legend
          verticalAlign="top"
          align="right"
          iconType="plainline"
          iconSize={14}
          wrapperStyle={{ fontSize: 11, color: "#5B6672", paddingBottom: 8 }}
        />
        {SERIES.map((item) => (
          <Line
            key={item.key}
            type="monotone"
            dataKey={item.key}
            name={item.name}
            stroke={item.color}
            strokeWidth={2}
            dot={false}
            activeDot={{ r: 4, strokeWidth: 2, stroke: CHART.surface }}
            isAnimationActive={false}
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  )
}
