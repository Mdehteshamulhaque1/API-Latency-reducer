"use client"

import { Area, AreaChart, ResponsiveContainer } from "recharts"

import { CHART } from "./chart-theme"

interface SparklineProps {
  values: number[]
  color?: string
  height?: number
  id: string
}

/** Tiny trend line for stat tiles. No axes, no tooltip (the tile carries the value). */
export function Sparkline({ values, color = CHART.avg, height = 36, id }: SparklineProps) {
  if (values.length < 2) return <div style={{ height }} />
  const data = values.map((value, index) => ({ index, value }))
  const gradientId = `spark-${id}`

  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 2, right: 0, left: 0, bottom: 0 }}>
        <defs>
          <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity={0.3} />
            <stop offset="100%" stopColor={color} stopOpacity={0} />
          </linearGradient>
        </defs>
        <Area
          type="monotone"
          dataKey="value"
          stroke={color}
          strokeWidth={1.5}
          fill={`url(#${gradientId})`}
          dot={false}
          isAnimationActive={false}
        />
      </AreaChart>
    </ResponsiveContainer>
  )
}
