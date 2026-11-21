"use client"

import { formatPercent } from "@/lib/utils"

import { CHART } from "./chart-theme"

interface CacheChartProps {
  totalRequests: number
  /** Cache hit rate as a percentage (0–100), matching the API summary. */
  hitRate: number
}

/**
 * Hit / miss split as a single proportional bar with direct labels.
 * A two-value comparison reads better as a part-to-whole bar than as a chart
 * with axes.
 */
export function CacheChart({ totalRequests, hitRate }: CacheChartProps) {
  const safeRate = Math.min(100, Math.max(0, Number.isFinite(hitRate) ? hitRate : 0))
  const hits = Math.round(totalRequests * (safeRate / 100))
  const misses = Math.max(totalRequests - hits, 0)

  if (totalRequests === 0) {
    return (
      <div className="flex h-[240px] items-center justify-center rounded-lg border border-dashed border-rule-strong text-sm text-graphite">
        No cacheable traffic yet
      </div>
    )
  }

  return (
    <div className="flex h-[240px] flex-col justify-center">
      <div className="flex items-end justify-between">
        <div>
          <p className="text-[12px] text-graphite">Hit rate</p>
          <p className="mt-1 font-mono text-4xl font-medium leading-none tracking-tight text-ink">
            {formatPercent(safeRate)}
          </p>
        </div>
        <p className="font-mono text-xs text-graphite">{totalRequests.toLocaleString()} requests</p>
      </div>

      <div
        role="img"
        aria-label={`${hits} cache hits and ${misses} misses`}
        className="mt-6 flex h-3 w-full gap-[2px] overflow-hidden"
      >
        <div
          className="h-full transition-[width] duration-500"
          style={{ width: `${safeRate}%`, background: CHART.hit }}
        />
        <div
          className="h-full flex-1 transition-[width] duration-500"
          style={{ background: CHART.miss }}
        />
      </div>

      <ul className="housing housing-row mt-5 grid grid-cols-2">
        <li className="p-3">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: CHART.hit }} />
            <span className="text-xs text-graphite">Hits</span>
          </div>
          <p className="mt-1.5 font-mono text-lg text-ink">{hits.toLocaleString()}</p>
          <p className="text-[11px] text-graphite">served from Redis</p>
        </li>
        <li className="p-3">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-sm" style={{ background: CHART.miss }} />
            <span className="text-xs text-graphite">Misses</span>
          </div>
          <p className="mt-1.5 font-mono text-lg text-ink">{misses.toLocaleString()}</p>
          <p className="text-[11px] text-graphite">went to the upstream</p>
        </li>
      </ul>
    </div>
  )
}
