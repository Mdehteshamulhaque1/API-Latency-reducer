"use client"

import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"

import type { LatencyPoint } from "@/lib/api"
import { parseUtc } from "@/lib/utils"

import { AXIS_TICK, CHART, TOOLTIP_ITEM_STYLE, TOOLTIP_LABEL_STYLE, TOOLTIP_STYLE } from "./chart-theme"

function formatTick(value: string): string {
  const date = parseUtc(value)
  if (Number.isNaN(date.getTime())) return value
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

/** Requests per bucket, stacked into successful vs errored. */
export function TrafficChart({ data, height = 240 }: { data: LatencyPoint[]; height?: number }) {
  const series = data.map((point) => ({
    label: formatTick(point.timestamp),
    ok: Math.max(point.request_count - point.error_count, 0),
    errors: point.error_count,
  }))

  if (series.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded-lg border border-dashed border-rule-strong text-sm text-graphite"
        style={{ height }}
      >
        No traffic in this window
      </div>
    )
  }

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={series} margin={{ top: 8, right: 8, left: -12, bottom: 0 }} barCategoryGap="30%">
        <CartesianGrid strokeDasharray="3 3" stroke={CHART.grid} vertical={false} />
        <XAxis dataKey="label" tick={AXIS_TICK} axisLine={false} tickLine={false} minTickGap={24} />
        <YAxis tick={AXIS_TICK} axisLine={false} tickLine={false} allowDecimals={false} width={56} />
        <Tooltip
          cursor={{ fill: "#F1F4F7" }}
          contentStyle={TOOLTIP_STYLE}
          labelStyle={TOOLTIP_LABEL_STYLE}
          itemStyle={TOOLTIP_ITEM_STYLE}
        />
        <Legend
          verticalAlign="top"
          align="right"
          iconType="square"
          iconSize={10}
          wrapperStyle={{ fontSize: 11, color: "#5B6672", paddingBottom: 8 }}
        />
        <Bar
          dataKey="ok"
          name="Successful"
          stackId="traffic"
          fill={CHART.ok}
          stroke={CHART.surface}
          strokeWidth={1}
          isAnimationActive={false}
        />
        <Bar
          dataKey="errors"
          name="Errors"
          stackId="traffic"
          fill={CHART.error}
          stroke={CHART.surface}
          strokeWidth={1}
          radius={[0, 0, 0, 0]}
          isAnimationActive={false}
        />
      </BarChart>
    </ResponsiveContainer>
  )
}
